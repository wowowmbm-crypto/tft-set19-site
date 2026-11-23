#!/usr/bin/env python3
"""Refresh registered Set 19 stats and discover strong unregistered comps."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import re
import unicodedata
import urllib.request

SOURCE_URL = "https://tft.ninja/comps?e=pbe"
SITE_FILE = Path(__file__).resolve().parents[1] / "index.html"
CANDIDATES_FILE = Path(__file__).resolve().parents[1] / "stats_candidates.json"
REGISTERED_SOURCES = {
    "hyperpop": "Ziggs Reroll",
    "renata": "Renata Glasc Reroll",
    "malz": "Malzahar Reroll",
    "ionic": "Vertical Ionic Spark (Jinx)",
    "beach": "Vertical Beach Pop (Taliyah)",
    "wall": "Juggernaut Graves",
    "renegade": "Vertical Renegade",
}
MIN_PLAY_RATE = 0.3
MAX_CANDIDATES = 12
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
NUMBER = r"([0-9]+(?:\.[0-9]+)?)"
AVP_RE = re.compile(NUMBER + r"\s*Adj\s*AVP\b", re.IGNORECASE)
WIN_RE = re.compile(NUMBER + r"\s*%\s*Win\s*%", re.IGNORECASE)
PLAY_RATE_RE = re.compile(NUMBER + r"\s*%\s*Play\s*Rate\b", re.IGNORECASE)


class Element:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []
        self.parent = None

    def text(self):
        return "".join(child.text() if isinstance(child, Element) else child for child in self.children)


class PageTree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Element(tag, attrs)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(node.tag in {"script", "style", "noscript"} for node in self.stack):
            self.stack[-1].children.append(data)


def elements(node):
    yield node
    for child in node.children:
        if isinstance(child, Element):
            yield from elements(child)


def headings(node):
    for child in elements(node):
        if child.tag in {"h1", "h2", "h3", "h4"}:
            yield child


def clean_text(value):
    return " ".join(value.split())


def parse_metrics(text):
    text = clean_text(text)
    avp_match = AVP_RE.search(text)
    win_match = WIN_RE.search(text)
    if not avp_match or not win_match:
        return None

    avp, win = float(avp_match.group(1)), float(win_match.group(1))
    if not 1 <= avp <= 8 or not 0 <= win <= 100:
        return None

    play_match = PLAY_RATE_RE.search(text)
    play_rate = float(play_match.group(1)) if play_match else None
    if play_rate is not None and not 0 <= play_rate <= 100:
        play_rate = None
    return {"avp": avp, "win": win, "play_rate": play_rate}


def card_for_heading(node):
    ancestor = node.parent
    while ancestor is not None and ancestor.tag not in {"body", "main", "document"}:
        # A card should contain one composition heading. This avoids treating
        # the whole list as the card for a page-level heading.
        if sum(1 for _ in headings(ancestor)) == 1:
            metrics = parse_metrics(ancestor.text())
            if metrics:
                return ancestor, metrics
        ancestor = ancestor.parent
    return None, None


def card_tier(card, title):
    if card is None:
        return None
    for node in elements(card):
        class_name = node.attrs.get("class", "").lower()
        if any(word in class_name for word in ("tier", "grade", "rank")):
            value = clean_text(node.text()).upper()
            if value in {"S", "A", "B", "C"}:
                return value

    prefix = clean_text(card.text()).split(title, 1)[0].strip()
    match = re.search(r"(?:^|[^A-Za-z])([SA])\s*$", prefix, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if prefix and prefix[-1].upper() in {"S", "A"}:
        return prefix[-1].upper()
    return None


def fetch_page():
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "TFT-Set19-Site-Stats-Updater/2.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"TFT Ninja returned HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")


def extract_source_comps(html):
    tree = PageTree()
    tree.feed(html)
    results = {}
    for node in headings(tree.root):
        title = clean_text(node.text())
        if not title:
            continue
        card, metrics = card_for_heading(node)
        if not card or not metrics:
            continue
        results.setdefault(title, {
            "title": title,
            "tier": card_tier(card, title),
            "avp": metrics["avp"],
            "win": metrics["win"],
            "play_rate": metrics["play_rate"],
        })
    if not results:
        raise RuntimeError("Could not find any composition statistics on TFT Ninja. No site data was changed.")
    return results


def normalize_title(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def registered_titles(site_html):
    titles = set(REGISTERED_SOURCES.values())
    # Use the site's own English labels too, so a recognized guide does not
    # reappear as a stats-only candidate when the source uses the same title.
    for _, _, english_name in re.findall(
        r"\{id:'([^']+)',name:'([^']*)',en:'([^']*)'", site_html
    ):
        titles.add(english_name)
    return {normalize_title(title) for title in titles if title}


def make_slug(title):
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:42] or "comp"
    suffix = hashlib.sha1(title.lower().encode("utf-8")).hexdigest()[:6]
    return f"{base}-{suffix}"


def find_candidates(source_comps, registered):
    candidates = []
    for title, comp in source_comps.items():
        if normalize_title(title) in registered:
            continue
        if comp["tier"] not in {"S", "A"}:
            continue
        if comp["play_rate"] is None or comp["play_rate"] < MIN_PLAY_RATE:
            continue
        candidates.append({
            "slug": make_slug(title),
            "title": title,
            "tier": comp["tier"],
            "avp": comp["avp"],
            "win": comp["win"],
            "play_rate": comp["play_rate"],
        })

    tier_order = {"S": 0, "A": 1}
    candidates.sort(key=lambda comp: (tier_order[comp["tier"]], comp["avp"], -comp["play_rate"], comp["title"].lower()))
    return candidates[:MAX_CANDIDATES]


def update_registered_stats(site_html, source_comps):
    updated = site_html
    matched = 0
    for comp_id, title in REGISTERED_SOURCES.items():
        source = source_comps.get(title)
        if source is None:
            print(f"No exact TFT Ninja match for {comp_id}; keeping its existing stats.")
            continue
        pattern = re.compile(
            rf"(?P<prefix>\b{re.escape(comp_id)}\s*:\s*\{{\s*avp\s*:\s*)[^,]+"
            rf"(?P<middle>\s*,\s*win\s*:\s*)[^,]+",
        )
        replacement = lambda match: (
            match.group("prefix") + f"{source['avp']:.2f}" +
            match.group("middle") + f"{source['win']:.1f}"
        )
        updated, count = pattern.subn(replacement, updated, count=1)
        if count != 1:
            raise RuntimeError(f"Could not safely update the registered stats entry for: {comp_id}")
        matched += 1
    return updated, matched


def update_checked_date(site_html, date):
    pattern = re.compile(r"const performanceCheckedAt=['\"][^'\"]*['\"];?")
    updated, count = pattern.subn(f"const performanceCheckedAt='{date}';", site_html, count=1)
    if count != 1:
        raise RuntimeError("Could not safely update the site's statistics date.")
    return updated


def write_outputs(source_comps):
    original_site = SITE_FILE.read_text(encoding="utf-8-sig")
    updated_site, matched = update_registered_stats(original_site, source_comps)
    now = datetime.now(timezone(timedelta(hours=9)))
    checked_at = now.strftime("%Y/%m/%d")
    updated_site = update_checked_date(updated_site, checked_at)

    candidates = find_candidates(source_comps, registered_titles(original_site))
    candidate_payload = {
        "checked_at": checked_at,
        "source": SOURCE_URL,
        "criteria": f"TFT Ninja S/A評価・直近1日・Pick率{MIN_PLAY_RATE:.1f}%以上",
        "candidates": candidates,
    }
    encoded_candidates = json.dumps(candidate_payload, ensure_ascii=False, indent=2) + "\n"

    if updated_site != original_site:
        SITE_FILE.write_text(updated_site, encoding="utf-8")
    previous_candidates = CANDIDATES_FILE.read_text(encoding="utf-8") if CANDIDATES_FILE.exists() else ""
    if encoded_candidates != previous_candidates:
        CANDIDATES_FILE.write_text(encoded_candidates, encoding="utf-8")

    print(f"Updated statistics for {matched} registered compositions.")
    print(f"Published {len(candidates)} unregistered S/A statistical candidates.")


if __name__ == "__main__":
    write_outputs(extract_source_comps(fetch_page()))
