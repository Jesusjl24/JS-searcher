"""
Social media enrichment using public APIs.
Fetches metadata for Reddit subreddits to give Claude more context.
"""

import logging
import requests
import time
from config import REDDIT_HEADERS

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"


def fetch_subreddit_info(subreddit_handle: str) -> dict | None:
    """
    Fetch public metadata for a subreddit via Reddit's JSON API.
    Returns dict with title, description, category, subscribers, or None on failure.
    """
    url = f"{REDDIT_BASE}/r/{subreddit_handle}/about.json"
    try:
        resp = requests.get(url, headers=REDDIT_HEADERS, timeout=8)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "title": data.get("title", ""),
            "description": data.get("public_description", "")[:300],
            "category": data.get("advertiser_category", ""),
            "subscribers": data.get("subscribers", 0),
            "over18": data.get("over18", False),
        }
    except Exception as e:
        logger.debug(f"Could not fetch info for r/{subreddit_handle}: {e}")
        return None


def enrich_sources(sources: list[dict]) -> list[dict]:
    """
    Enrich source dicts with metadata where possible.
    Currently enriches Reddit subreddits via the public JSON API.
    """
    enriched = []
    for source in sources:
        s = source.copy()
        if s.get("platform") == "reddit" and s.get("handle"):
            info = fetch_subreddit_info(s["handle"])
            if info:
                s["meta"] = info
                # Build a richer name string for Claude
                desc = info.get("description") or ""
                title = info.get("title") or s["name"]
                s["display"] = f"{title} (r/{s['handle']}) — {desc[:150]}" if desc else title
            else:
                s["display"] = s["name"]
            time.sleep(0.3)  # respectful pacing
        else:
            s["display"] = s["name"]
        enriched.append(s)
    return enriched
