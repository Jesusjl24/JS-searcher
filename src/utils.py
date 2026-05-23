"""Shared utilities for Media Diet Diagnostic"""

import logging
import re
from config import LOGGING_CONFIG, BIAS_LABELS, BIAS_COLORS


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, LOGGING_CONFIG["level"]),
        format=LOGGING_CONFIG["format"],
    )


def get_bias_label(score: float) -> str:
    for (low, high), label in BIAS_LABELS.items():
        if low <= score <= high:
            return label
    return "Center"


def get_bias_color(score: float) -> str:
    label = get_bias_label(score)
    return BIAS_COLORS.get(label, "#78909c")


def parse_source_line(line: str) -> dict | None:
    """
    Parse a single line of user input into a structured source dict.
    Handles: @handle, r/subreddit, youtube.com/... URLs, plain names.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    source = {"raw": line, "platform": "unknown", "name": line}

    # Reddit subreddit
    reddit_match = re.match(r"(?:https?://(?:www\.)?reddit\.com)?/?r/(\w+)", line, re.I)
    if reddit_match:
        source["platform"] = "reddit"
        source["name"] = f"r/{reddit_match.group(1)}"
        source["handle"] = reddit_match.group(1)
        return source

    # Twitter/X @handle
    if re.match(r"^@\w+$", line):
        source["platform"] = "twitter"
        source["name"] = line
        source["handle"] = line.lstrip("@")
        return source

    # Twitter/X URL
    twitter_url = re.match(r"https?://(?:www\.)?(?:twitter|x)\.com/(\w+)", line, re.I)
    if twitter_url:
        source["platform"] = "twitter"
        source["name"] = f"@{twitter_url.group(1)}"
        source["handle"] = twitter_url.group(1)
        return source

    # YouTube URL or channel
    if "youtube.com" in line.lower() or "youtu.be" in line.lower():
        source["platform"] = "youtube"
        yt_match = re.search(r"(?:channel/|@|c/)([^/?&\s]+)", line, re.I)
        if yt_match:
            source["name"] = yt_match.group(1)
            source["handle"] = yt_match.group(1)
        return source

    # Generic URL → website/news source
    if re.match(r"https?://", line, re.I):
        source["platform"] = "website"
        domain = re.search(r"https?://(?:www\.)?([^/\s]+)", line, re.I)
        if domain:
            source["name"] = domain.group(1)
        return source

    # Bare subreddit: starts with r/
    if line.lower().startswith("r/"):
        source["platform"] = "reddit"
        source["name"] = line
        source["handle"] = line[2:]
        return source

    # Everything else treated as a name/keyword
    return source


def parse_sources_text(text: str) -> list[dict]:
    """Parse multi-line user input into a list of source dicts."""
    sources = []
    for line in text.splitlines():
        parsed = parse_source_line(line)
        if parsed:
            sources.append(parsed)
    return sources
