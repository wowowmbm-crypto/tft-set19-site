#!/usr/bin/env python3
"""Refresh matched Set 19 PBE statistics from TFT Ninja."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.request

SOURCE_URL = "https://tft.ninja/comps?e=pbe"
SITE_FILE = Path(__file__).resolve().parents[1] / "index.html"
COMPS = {
    "hyperpop": "Ziggs Reroll",
    "renata": "Renata Glasc Reroll",
    "malz": "Malzahar Reroll",
    "ionic": "Vertical Ionic Spark (Jinx)",
    "beach": "Vertical Beach Pop (Taliyah)",
    "wall": "Juggernaut Graves",
    "renegade": "Vertical Renegade",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Element:
    def __init__(self, tag):
        self.tag, self.children, self.parent = tag, [], None

    def text(self):
        return "".join(child.text() if isinstance(child, Element) else child for child in self.children)


class PageTree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Element(tag)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if not any(node.tag in {"script", "style", "noscript"} for node in self.stack):
            self.stack[-1].children.append(data)


def headings(node):
    if node.tag in {"h1", "h2", "h3", "h4"}:
        yield node
    for child in node.children:
        if isinstance(child, Element):
            yield from headings(child)


def fetch_page():
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "TFT-Set19-Site-Stats-Updater/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"TFT Ninja returned HTTP {response.status}")
        return response.read().decode("utf-8", errors="replace")


def extract_metrics(html):
    tree = PageTree()
    tree.feed(html)
    title_nodes = {node.text().strip(): node for node in headings(tree.root)}
    results = {}
    for comp_id, title in COMPS.items():
        node = title_nodes.get(title)
        if node is None:
            raise RuntimeError(f"Could not find source row: {title}")
        ancestor = node.parent
        metrics = None
        while ancestor is not None and ancestor.tag not in {"body", "main", "document"}:
            text = " ".join(ancestor.text().split())
            if title in text and "ADJ AVP" in text and "WIN%" in text:
                avp_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s+ADJ AVP", text)
                win_match = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s+WIN%", text)
                if avp_match and win_match:
                    avp, win = float(avp_match.group(1)), float(win_match.group(1))
                    if 1 <= avp <= 8 and 0 <= win <= 100:
                        metrics = avp, win
                        break
            ancestor = ancestor.parent
        if metrics is None:
            raise RuntimeError(f"Could not read safe AVP and Win% values for: {title}")
        results[comp_id] = metrics
    return results


def update_site(metrics):
    original = SITE_FILE.read_text(encoding="utf-8-sig")
    updated = original
    for comp_id, (avp, win) in metrics.items():
        marker = f"{comp_id}:{{avp:"
        start = updated.find(marker)
        if start < 0:
            raise RuntimeError(f"Could not update current stats for: {comp_id}")
        avp_start = start + len(marker)
        avp_end = updated.index(",", avp_start)
        updated = updated[:avp_start] + f"{avp:.2f}" + updated[avp_end:]
        win_start = updated.index(",win:", start) + len(",win:")
        win_end = updated.index(",", win_start)
        updated = updated[:win_start] + f"{win:.1f}" + updated[win_end:]

    date = datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d")
    date_marker = "const performanceCheckedAt='"
    date_start = updated.index(date_marker) + len(date_marker)
    date_end = updated.index("';", date_start)
    updated = updated[:date_start] + date + updated[date_end:]
    if updated != original:
        SITE_FILE.write_text(updated, encoding="utf-8")
        print("Updated matched TFT Ninja statistics.")
    else:
        print("Statistics are already current.")


if __name__ == "__main__":
    update_site(extract_metrics(fetch_page()))
