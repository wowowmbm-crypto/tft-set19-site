#!/usr/bin/env python3
"""Refresh recent public TFT posts and videos for the site's pickup strip."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = ROOT / "sns_pickups.json"
X_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
X_QUERY = '(TFT OR "Teamfight Tactics") ("Set 19" OR Set19 OR #TFTSet19 OR comp OR comps OR reroll OR 構成 OR リロール) -is:retweet'
WINDOW = timedelta(days=3)
MAX_PER_SOURCE = 3
MAX_ITEMS = MAX_PER_SOURCE * 2
USER_AGENT = "TFT-Set19-Site-Social-Updater/1.0"


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def get_json(url, params, headers=None, service="source"):
    request_url = f"{url}?{urlencode(params)}"
    request_headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    request = Request(request_url, headers=request_headers)
    try:
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"{service} returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        # Do not echo request URLs or response bodies: they can contain API keys.
        raise RuntimeError(f"{service} returned HTTP {error.code}") from None
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{service} request failed ({type(error).__name__})") from None


def compact_text(value, limit):
    text = re.sub(r"https?://\S+", "", str(value or ""))
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit - 1].rstrip() + "…"
    return text


def metric_count(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def fetch_x(token, cutoff):
    payload = get_json(
        X_SEARCH_URL,
        {
            "query": X_QUERY,
            "start_time": isoformat(cutoff),
            "max_results": 100,
            "tweet.fields": "created_at,author_id,public_metrics,lang",
            "expansions": "author_id",
            "user.fields": "username,name",
        },
        headers={"Authorization": f"Bearer {token}"},
        service="X API",
    )
    users = {
        user.get("id"): user
        for user in payload.get("includes", {}).get("users", [])
        if user.get("id")
    }
    items = []
    for post in payload.get("data", []):
        posted = parse_time(post.get("created_at"))
        if posted is None or posted < cutoff:
            continue
        text = compact_text(post.get("text"), 500)
        if not text:
            continue
        metrics = post.get("public_metrics") or {}
        impressions = metric_count(metrics.get("impression_count"))
        likes = metric_count(metrics.get("like_count"))
        reposts = metric_count(metrics.get("retweet_count"))
        replies = metric_count(metrics.get("reply_count"))
        username = (users.get(post.get("author_id")) or {}).get("username", "")
        first_line = re.split(r"(?<=[。.!?])\s+|\n", text, maxsplit=1)[0]
        items.append({
            "id": f"x-{post.get('id', '')}",
            "source": "X",
            "url": f"https://x.com/{username}/status/{post.get('id', '')}" if username else f"https://x.com/i/web/status/{post.get('id', '')}",
            "published_at": isoformat(posted),
            "title": compact_text(first_line or text, 58),
            "summary": f"@{username} · {compact_text(text, 104)}" if username else compact_text(text, 120),
            "metric_label": "表示" if impressions else "いいね",
            "metric_count": impressions or likes,
            "engagement_score": impressions + likes * 10 + reposts * 20 + replies * 12,
        })
    items.sort(key=lambda item: (item["engagement_score"], item["published_at"]), reverse=True)
    return items[:MAX_PER_SOURCE]


def fetch_youtube(api_key, cutoff):
    search = get_json(
        YOUTUBE_SEARCH_URL,
        {
            "part": "snippet",
            "q": "TFT Set 19",
            "type": "video",
            "publishedAfter": isoformat(cutoff),
            "order": "viewCount",
            "regionCode": "JP",
            "relevanceLanguage": "ja",
            "maxResults": 25,
            "key": api_key,
        },
        service="YouTube Data API search",
    )
    video_ids = [
        entry.get("id", {}).get("videoId")
        for entry in search.get("items", [])
        if entry.get("id", {}).get("videoId")
    ]
    if not video_ids:
        return []

    details = get_json(
        YOUTUBE_VIDEOS_URL,
        {"part": "snippet,statistics", "id": ",".join(video_ids), "key": api_key},
        service="YouTube Data API videos",
    )
    items = []
    for video in details.get("items", []):
        snippet = video.get("snippet") or {}
        posted = parse_time(snippet.get("publishedAt"))
        if posted is None or posted < cutoff:
            continue
        video_id = video.get("id")
        if not video_id:
            continue
        views = metric_count((video.get("statistics") or {}).get("viewCount"))
        description = compact_text(snippet.get("description"), 90)
        channel = compact_text(snippet.get("channelTitle"), 44)
        items.append({
            "id": f"youtube-{video_id}",
            "source": "YouTube",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": isoformat(posted),
            "title": compact_text(snippet.get("title"), 72),
            "summary": " · ".join(part for part in (channel, description) if part),
            "metric_label": "再生",
            "metric_count": views,
            "engagement_score": views,
        })
    items.sort(key=lambda item: (item["engagement_score"], item["published_at"]), reverse=True)
    return items[:MAX_PER_SOURCE]


def read_previous():
    if not OUTPUT_FILE.exists():
        return {"checked_at": "", "sources": {}, "items": []}
    try:
        value = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("items"), list):
            return value
    except (OSError, json.JSONDecodeError):
        pass
    return {"checked_at": "", "sources": {}, "items": []}


def save_payload(previous, now, cutoff, refreshed):
    by_source = {"X": [], "YouTube": []}
    for item in previous.get("items", []):
        source = item.get("source")
        posted = parse_time(item.get("published_at"))
        if source in by_source and posted and cutoff <= posted <= now:
            by_source[source].append(item)

    sources = previous.get("sources") if isinstance(previous.get("sources"), dict) else {}
    for source, new_items in refreshed.items():
        by_source[source] = new_items
        sources[source] = {"checked_at": isoformat(now), "status": "ok"}

    items = []
    for source in ("X", "YouTube"):
        unique = {}
        for item in by_source[source]:
            unique[item["id"]] = item
        source_items = sorted(
            unique.values(), key=lambda item: (item.get("engagement_score", 0), item.get("published_at", "")), reverse=True
        )[:MAX_PER_SOURCE]
        items.extend(source_items)
    items.sort(key=lambda item: item.get("published_at", ""), reverse=True)

    payload = {
        "checked_at": now.astimezone(timezone(timedelta(hours=9))).strftime("%Y/%m/%d"),
        "window_hours": 72,
        "sources": sources,
        "items": items[:MAX_ITEMS],
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated SNS pickup data: X={len(by_source['X'])}, YouTube={len(by_source['YouTube'])} items.")


def main():
    now = utc_now()
    cutoff = now - WINDOW
    previous = read_previous()
    refreshed = {}
    warnings = []

    x_token = os.environ.get("X_BEARER_TOKEN", "").strip()
    youtube_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if x_token:
        try:
            refreshed["X"] = fetch_x(x_token, cutoff)
        except RuntimeError as error:
            warnings.append(str(error))
    else:
        warnings.append("X update skipped: X_BEARER_TOKEN repository secret is not configured.")

    if youtube_key:
        try:
            refreshed["YouTube"] = fetch_youtube(youtube_key, cutoff)
        except RuntimeError as error:
            warnings.append(str(error))
    else:
        warnings.append("YouTube update skipped: YOUTUBE_API_KEY repository secret is not configured.")

    if refreshed:
        save_payload(previous, now, cutoff, refreshed)
    else:
        print("No SNS source was refreshed; the last published pickup data was kept.")

    for warning in warnings:
        print(f"::warning::{warning}")
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
