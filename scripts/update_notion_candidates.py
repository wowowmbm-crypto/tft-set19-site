#!/usr/bin/env python3
"""Read recent Set 19 article metadata from the shared Notion database."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "notion_candidates.json"
DEFAULT_DATABASE_ID = "1d3859a65b0a80f8adc3c0378eb3b007"
NOTION_VERSION = "2026-03-11"
NOTION_API = "https://api.notion.com/v1"
MAX_ITEMS = 12
MAX_AGE = timedelta(days=90)


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_payload():
    try:
        payload = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) and isinstance(payload.get("items"), list) else {"items": []}
    except (OSError, json.JSONDecodeError):
        return {"items": []}


def request_json(token, method, url, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "TFT-Set19-Notion-Candidates/1.0",
    })
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(f"Notion API returned HTTP {error.code}") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Notion API request failed ({type(error).__name__})") from None


def text_value(value):
    if not isinstance(value, dict):
        return ""
    kind = value.get("type")
    if kind in ("title", "rich_text"):
        return "".join(part.get("plain_text", "") for part in value.get(kind, []) if isinstance(part, dict)).strip()
    if kind in ("select", "status"):
        return str((value.get(kind) or {}).get("name", "")).strip()
    if kind == "multi_select":
        return ", ".join(item.get("name", "") for item in value.get(kind, []) if isinstance(item, dict))
    if kind == "url":
        return str(value.get("url") or "").strip()
    if kind == "date":
        return str((value.get("date") or {}).get("start", "")).strip()
    if kind == "number":
        number = value.get("number")
        return str(number) if number is not None else ""
    if kind == "checkbox":
        return "true" if value.get("checkbox") else ""
    if kind == "people":
        return ", ".join(person.get("name", "") for person in value.get("people", []) if isinstance(person, dict))
    return ""


def properties_of(page):
    props = page.get("properties")
    return props if isinstance(props, dict) else {}


def property_by_hint(props, pattern):
    for name, value in props.items():
        if re.search(pattern, str(name), flags=re.I):
            candidate = text_value(value)
            if candidate:
                return candidate
    return ""


def page_title(props):
    for name, value in props.items():
        if isinstance(value, dict) and value.get("type") == "title":
            title = text_value(value)
            if title:
                return title
    return property_by_hint(props, r"title|名前|記事|構成")


def data_source_id(token, database_id):
    database = request_json(token, "GET", f"{NOTION_API}/databases/{quote(database_id, safe='')}")
    sources = database.get("data_sources") or []
    if not sources:
        raise RuntimeError("Notion database has no readable data source")
    return sources[0].get("id")


def query_pages(token, source_id):
    pages = []
    cursor = None
    for _ in range(10):
        body = {"page_size": 100, "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
        if cursor:
            body["start_cursor"] = cursor
        result = request_json(token, "POST", f"{NOTION_API}/data_sources/{quote(source_id, safe='')}/query", body)
        pages.extend(result.get("results", []))
        if not result.get("has_more") or not result.get("next_cursor"):
            break
        cursor = result["next_cursor"]
    return pages


def extract_candidates(pages, now):
    cutoff = now - MAX_AGE
    candidates = []
    for page in pages:
        props = properties_of(page)
        title = page_title(props)
        url = page.get("url", "")
        if not title or not url.startswith("https://") or "notion.site" not in url:
            continue
        date_text = property_by_hint(props, r"投稿日|公開日|日付|date|published")
        date_text = date_text or page.get("created_time") or page.get("last_edited_time") or ""
        try:
            published = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except (TypeError, ValueError):
            published = None
        if published and not (cutoff <= published <= now + timedelta(days=1)):
            continue
        candidates.append({
            "id": page.get("id", ""),
            "title": title[:160],
            "url": url,
            "published_at": iso(published) if published else "",
            "author": property_by_hint(props, r"投稿者|author|writer|翻訳者")[:80],
            "patch": property_by_hint(props, r"パッチ|patch|^set$|set\s*\d+")[:40],
        })
    candidates.sort(key=lambda item: item.get("published_at", ""), reverse=True)
    return candidates[:MAX_ITEMS]


def save(payload):
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    now = now_utc()
    previous = read_payload()
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        if previous.get("status") != "not_configured":
            previous["status"] = "not_configured"
            previous.pop("message", None)
            save(previous)
        print("Notion candidate refresh skipped: NOTION_API_KEY is not configured.")
        return
    database_id = os.environ.get("NOTION_DATABASE_ID", DEFAULT_DATABASE_ID).strip()
    try:
        source_id = data_source_id(token, database_id)
        pages = query_pages(token, source_id)
        items = extract_candidates(pages, now)
    except RuntimeError as error:
        payload = dict(previous)
        payload["status"] = "error"
        if previous.get("status") != "error":
            payload["last_attempt_at"] = iso(now)
            payload["message"] = str(error)
            save(payload)
        print(f"::warning::{error}")
        return

    save({
        "status": "ok",
        "checked_at": iso(now),
        "last_attempt_at": iso(now),
        "items": items,
        "source_url": "https://busy-ziconium-740.notion.site/1d3859a65b0a80f8adc3c0378eb3b007",
    })
    print(f"Updated Notion article candidates: {len(items)} items.")


if __name__ == "__main__":
    main()
