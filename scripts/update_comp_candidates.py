#!/usr/bin/env python3
"""Merge Set 19 comp leads from public guides, stats, and the shared Notion index."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import hashlib
import json
import os
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
SITE_FILE = ROOT / "index.html"
STATS_FILE = ROOT / "stats_candidates.json"
NOTION_FILE = ROOT / "notion_candidates.json"
OUTPUT_FILE = ROOT / "comp_candidates.json"
USER_AGENT = "TFT-Set19-Comp-Candidate-Scanner/1.0"
MAX_ARTICLES = 12

FEEDS = {
    "mobalytics": {
        "name": "Mobalytics",
        "url": "https://mobalytics.gg/tft/guides/best-tft-pbe-comps",
    },
    "tft_coach": {
        "name": "TFT Coach",
        "url": "https://tftcoach.com/set-19/comps",
    },
}

# These aliases combine alternate guide names for one lineup and prevent a
# known guide from appearing again as an unregistered composition candidate.
ALIAS_GROUPS = {
    "registered:hyperpop": ["Hyperpop Reroll", "Hype Train", "Hyperpop Ziggs"],
    "registered:renata": ["Renata Guards", "Renata & the Bouncers", "Renata and the Bouncers", "Bodyguard Renata"],
    "registered:malz": ["Malzahar Prodigy", "Malzart", "Prodigy Malzahar"],
    "registered:ionic": ["Ionic Spark", "Ionic Icons", "Ionic Spark Jinx"],
    "registered:beach": ["Beach Pop", "Beach Party", "Beach Pop Graves"],
    "registered:gufeng": ["Gu Feng", "Gu Feng Groove", "Gu Feng Xayah"],
    "registered:disco": ["Nine at the Disco"],
    "registered:wall": ["Wall of Sound"],
    "registered:renegade": ["Renegade Radio"],
    "registered:kda": ["K/DA Rising Stars"],
    "candidate:classical-jhin": ["Classical Carnage", "Classical Jhin"],
    "candidate:slayer-viego": ["Slayin Alive", "Slayer Viego"],
    "candidate:rock-vayne": ["We Will Rock You", "Rock Vayne"],
}
ALIAS_LOOKUP = {}
for group, names in ALIAS_GROUPS.items():
    for name in names:
        key = re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower())
        if key:
            ALIAS_LOOKUP[key] = group


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_title(value):
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def group_key(title):
    normalized = normalize_title(title)
    return ALIAS_LOOKUP.get(normalized, "title:" + normalized)


def clean_text(value):
    return " ".join(str(value or "").split()).strip()


def read_json(path, fallback):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


class ListingParser(HTMLParser):
    """Collect rendered headings and links without third-party dependencies."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings = []
        self.heading_entries = []
        self.links = []
        self._heading = None
        self._link = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading is None:
            self._heading = {"tag": tag, "parts": []}
        if tag == "a" and self._link is None:
            self._link = {"href": attributes.get("href", ""), "parts": []}

    def handle_data(self, data):
        if self._heading is not None:
            self._heading["parts"].append(data)
        if self._link is not None:
            self._link["parts"].append(data)

    def handle_endtag(self, tag):
        if self._heading is not None and tag == self._heading["tag"]:
            text = clean_text("".join(self._heading["parts"]))
            if text:
                self.headings.append(text)
                self.heading_entries.append({"tag": self._heading["tag"], "text": text})
            self._heading = None
        if self._link is not None and tag == "a":
            text = clean_text("".join(self._link["parts"]))
            if text and self._link["href"]:
                self.links.append({"text": text, "href": self._link["href"]})
            self._link = None


def fetch_html(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(request, timeout=25) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}") from None
    except (URLError, TimeoutError) as error:
        raise RuntimeError(type(error).__name__) from None


def valid_source_url(url, hosts):
    try:
        parsed = urlparse(url)
        return parsed.scheme == "https" and any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in hosts)
    except (AttributeError, ValueError):
        return False


def parse_mobalytics(html):
    parser = ListingParser()
    parser.feed(html)
    guide_links = {}
    for link in parser.links:
        label = re.sub(r"\s+(?:TFT\s+)?Comp\s+Guide\s*[↗↗]*$", "", link["text"], flags=re.I).strip()
        if label != link["text"]:
            absolute = urljoin(FEEDS["mobalytics"]["url"], link["href"])
            if valid_source_url(absolute, {"mobalytics.gg"}):
                guide_links[normalize_title(label)] = absolute

    items = {}
    for heading in parser.headings:
        match = re.match(r"([SA])\s*[- ]\s*tier\s*:\s*(.+)$", heading, flags=re.I)
        if not match:
            continue
        tier, title = match.group(1).upper(), clean_text(match.group(2))
        title = re.sub(r"\s+(?:Comp\s+Guide|Guide)\s*$", "", title, flags=re.I).strip()
        key = normalize_title(title)
        if not key or key in items:
            continue
        items[key] = {
            "title": title,
            "tier": tier,
            "url": guide_links.get(key, FEEDS["mobalytics"]["url"]),
        }
    if not items:
        raise RuntimeError("No S/A guide entries found; keeping the previous source snapshot")
    return list(items.values())


def parse_tft_coach(html):
    parser = ListingParser()
    parser.feed(html)

    # The listing uses in-page anchors for its comp table, so its URLs may
    # resolve to /set-19/comps#... instead of a nested /comps/<slug> route.
    # Match linked labels to real section headings instead of assuming a URL
    # shape that the site does not use.
    heading_keys = {
        normalize_title(entry["text"])
        for entry in parser.heading_entries
        if entry["tag"] in {"h2", "h3"} and len(normalize_title(entry["text"])) >= 4
    }
    items = {}
    for link in parser.links:
        title = clean_text(link["text"])
        key = normalize_title(title)
        if len(key) < 4 or key not in heading_keys:
            continue
        absolute = urljoin(FEEDS["tft_coach"]["url"], link["href"])
        parsed = urlparse(absolute)
        if parsed.hostname != "tftcoach.com" or not parsed.path.startswith("/set-19/comps"):
            continue
        items.setdefault(key, {"title": title, "tier": None, "url": absolute})

    # Keep discovery useful if the source removes the table links but retains
    # its heading outline. Comp names are h3 sections; prose subheadings and
    # FAQ questions are excluded.
    if not items:
        excluded = {
            "reroll comps", "fast 8 comps: 4-cost carries", "fast 9 comps: late-game boards",
            "the 15 comps at a glance", "faq", "know the set before you pick a comp",
        }
        excluded_keys = {normalize_title(name) for name in excluded}
        for entry in parser.heading_entries:
            title = clean_text(entry["text"])
            key = normalize_title(title)
            lowered = title.lower()
            if entry["tag"] != "h3" or len(key) < 4 or key in excluded_keys:
                continue
            if lowered.startswith(("board ", "traits", "how to ", "what to ", "items", "to unlock", "what are ", "which ", "do i ", "is this ")):
                continue
            items.setdefault(key, {"title": title, "tier": None, "url": FEEDS["tft_coach"]["url"]})

    if not items:
        raise RuntimeError("No Set 19 composition entries found; keeping the previous source snapshot")
    return list(items.values())


def refresh_feed(source_id, previous, now):
    config = FEEDS[source_id]
    old = previous.get(source_id, {}) if isinstance(previous, dict) else {}
    parser = parse_mobalytics if source_id == "mobalytics" else parse_tft_coach
    try:
        items = parser(fetch_html(config["url"]))
        return {
            "status": "ok",
            "name": config["name"],
            "checked_at": iso(now),
            "last_attempt_at": iso(now),
            "url": config["url"],
            "items": items,
        }
    except (RuntimeError, OSError, ValueError) as error:
        print(f"::warning::{config['name']} candidate scan failed: {error}")
        cached = old.get("items", []) if isinstance(old, dict) else []
        return {
            "status": "stale" if cached else "error",
            "name": config["name"],
            "checked_at": old.get("checked_at", "") if isinstance(old, dict) else "",
            "last_attempt_at": iso(now),
            "url": config["url"],
            "items": cached if isinstance(cached, list) else [],
        }


def registered_groups(site_html):
    registered = set()
    for match in re.finditer(r"\{id:'([^']+)',name:'([^']*)',en:'([^']*)'", site_html):
        comp_id, _, english = match.groups()
        if comp_id:
            registered.add("registered:" + comp_id)
        if english:
            registered.add(group_key(english))
    return registered


def candidate_id(key):
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def source_record(source_id, item, checked_at):
    record = {
        "id": source_id,
        "name": "TFT Ninja" if source_id == "tft_ninja" else FEEDS.get(source_id, {}).get("name", "Notion"),
        "title": clean_text(item.get("title"))[:160],
        "url": item.get("url") or FEEDS.get(source_id, {}).get("url", ""),
        "checked_at": checked_at or "",
    }
    if item.get("tier") in {"S", "A", "B", "C"}:
        record["tier"] = item["tier"]
    for key, maximum in (("avp", 8), ("win", 100), ("play_rate", 100)):
        try:
            value = float(item.get(key))
        except (TypeError, ValueError):
            continue
        if 0 <= value <= maximum:
            record[key] = value
    return record


def build_candidate_data(site_html, stats_payload, notion_payload, feeds, now):
    registered = registered_groups(site_html)
    groups = {}

    def add_candidate(source_id, item, checked_at):
        title = clean_text(item.get("title"))
        key = group_key(title)
        if len(normalize_title(title)) < 4 or key in registered:
            return
        record = groups.setdefault(key, {"key": key, "titles": [], "sources": []})
        if title not in record["titles"]:
            record["titles"].append(title)
        source = source_record(source_id, item, checked_at)
        if source["url"] and not valid_source_url(source["url"], {"tft.ninja", "mobalytics.gg", "tftcoach.com", "notion.site"}):
            source["url"] = FEEDS.get(source_id, {}).get("url", "")
        if not any(existing["id"] == source["id"] and existing["url"] == source["url"] for existing in record["sources"]):
            record["sources"].append(source)

    stats_checked = stats_payload.get("checked_at", "")
    stats_items = stats_payload.get("candidates", [])
    if isinstance(stats_items, list):
        for item in stats_items:
            if isinstance(item, dict):
                add_candidate("tft_ninja", item, stats_checked)
    for source_id, feed in feeds.items():
        checked = feed.get("checked_at", "")
        for item in feed.get("items", []):
            if isinstance(item, dict):
                add_candidate(source_id, item, checked)

    notion_items = notion_payload.get("items", []) if isinstance(notion_payload.get("items"), list) else []
    articles = []
    for article in notion_items:
        if not isinstance(article, dict) or not article.get("title") or not valid_source_url(article.get("url", ""), {"notion.site"}):
            continue
        article_title = clean_text(article.get("title"))[:160]
        normalized_article = normalize_title(article_title)
        matched = False
        for record in groups.values():
            for title in record["titles"]:
                normalized_title = normalize_title(title)
                if len(normalized_title) >= 7 and (normalized_title in normalized_article or normalized_article in normalized_title):
                    record["sources"].append(source_record("notion", article, notion_payload.get("checked_at", "")))
                    matched = True
                    break
            if matched:
                break
        if not matched:
            articles.append({
                "title": article_title,
                "url": article["url"],
                "published_at": article.get("published_at", ""),
                "author": clean_text(article.get("author", ""))[:80],
                "patch": clean_text(article.get("patch", ""))[:40],
            })

    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    candidates = []
    for key, record in groups.items():
        # Prefer the source with a published tier when choosing the card title.
        record["sources"].sort(key=lambda source: (source.get("tier") is None, tier_order.get(source.get("tier"), 4), source["id"]))
        preferred = next((source["title"] for source in record["sources"] if source["id"] == "mobalytics"), None)
        title = preferred or next((source["title"] for source in record["sources"] if source["id"] == "tft_coach"), None) or record["titles"][0]
        stats = next((source for source in record["sources"] if source["id"] == "tft_ninja"), None)
        tier = next((source.get("tier") for source in record["sources"] if source.get("tier") in {"S", "A", "B", "C"}), None)
        candidates.append({
            "id": candidate_id(key),
            "name": title,
            "tier": tier,
            "statistical": bool(stats),
            "source_count": len({source["id"] for source in record["sources"]}),
            "sources": record["sources"],
        })
    candidates.sort(key=lambda item: (
        -int(item["source_count"] >= 2),
        tier_order.get(item["tier"], 4),
        -int(item["statistical"]),
        item["name"].lower(),
    ))
    articles.sort(key=lambda item: item.get("published_at", ""), reverse=True)

    source_status = {
        "tft_ninja": {
            "name": "TFT Ninja",
            "status": "ok" if stats_payload.get("source") else "unknown",
            "checked_at": stats_checked,
            "count": len(stats_items) if isinstance(stats_items, list) else 0,
            "url": stats_payload.get("source", "https://tft.ninja/comps?e=pbe"),
        },
        "mobalytics": {key: feeds["mobalytics"].get(key) for key in ("name", "status", "checked_at", "last_attempt_at", "url")},
        "tft_coach": {key: feeds["tft_coach"].get(key) for key in ("name", "status", "checked_at", "last_attempt_at", "url")},
        "notion": {
            "name": "Notion",
            "status": notion_payload.get("status", "unknown"),
            "checked_at": notion_payload.get("checked_at", ""),
            "count": len(notion_items),
            "url": notion_payload.get("source_url", ""),
        },
    }
    return {
        "checked_at": iso(now),
        "sources": source_status,
        "candidates": candidates,
        "articles": articles[:MAX_ARTICLES],
        "note": "候補発見用です。統計・ガイドの掲載内容を確認する前に、盤面や装備を構成ガイドへ自動登録しません。",
    }


def main():
    now = utc_now()
    previous = read_json(OUTPUT_FILE, {})
    previous_feeds = previous.get("feeds", {}) if isinstance(previous.get("feeds"), dict) else {}
    # A committed candidate snapshot can seed the per-source cache. This keeps
    # the visible list if the first scheduled scrape is blocked.
    previous_candidates = previous.get("candidates", []) if isinstance(previous.get("candidates"), list) else []
    previous_feeds = {key: dict(value) for key, value in previous_feeds.items() if isinstance(value, dict)}
    for source_id in FEEDS:
        cached_feed = previous_feeds.setdefault(source_id, {})
        if cached_feed.get("items"):
            continue
        cached_items = {}
        for candidate in previous_candidates:
            if not isinstance(candidate, dict):
                continue
            for source in candidate.get("sources", []):
                if not isinstance(source, dict) or source.get("id") != source_id:
                    continue
                title = clean_text(source.get("title"))
                if title:
                    cached_items.setdefault(normalize_title(title), {
                        "title": title,
                        "tier": source.get("tier"),
                        "url": source.get("url", FEEDS[source_id]["url"]),
                    })
        if cached_items:
            cached_feed["items"] = list(cached_items.values())
            cached_feed.setdefault("checked_at", "")
    feeds = {source_id: refresh_feed(source_id, previous_feeds, now) for source_id in FEEDS}
    site_html = SITE_FILE.read_text(encoding="utf-8-sig")
    stats_payload = read_json(STATS_FILE, {"candidates": []})
    notion_payload = read_json(NOTION_FILE, {"status": "not_configured", "items": []})
    payload = build_candidate_data(site_html, stats_payload, notion_payload, feeds, now)
    if os.environ.get("TFT_NINJA_REFRESH_STATUS") == "failure":
        payload["sources"]["tft_ninja"]["status"] = "stale"
    payload["feeds"] = feeds
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published {len(payload['candidates'])} unregistered composition candidates from multi-source discovery.")
    print(f"Included {len(payload['articles'])} recent Notion article leads.")
    for source_id, feed in feeds.items():
        print(f"{FEEDS[source_id]['name']} source status: {feed['status']} ({len(feed.get('items', []))} entries).")


if __name__ == "__main__":
    main()
