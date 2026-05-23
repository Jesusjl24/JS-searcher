"""
Configuration for Media Diet Diagnostic Tool
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_CONFIG = {
    "page_title": "Media Diet Diagnostic",
    "page_icon": "🔬",
    "layout": "wide",
}

CLAUDE_CONFIG = {
    "source_analysis_model": "claude-haiku-4-5-20251001",
    "diet_analysis_model": "claude-sonnet-4-6",
    "max_sources_per_batch": 15,
    "max_tokens_source": 4096,
    "max_tokens_diet": 2048,
    "timeout": 60,
}

BIAS_LABELS = {
    (-10, -6): "Far Left",
    (-6, -3): "Left",
    (-3, -1): "Center-Left",
    (-1, 1): "Center",
    (1, 3): "Center-Right",
    (3, 6): "Right",
    (6, 10): "Far Right",
}

BIAS_COLORS = {
    "Far Left": "#1a237e",
    "Left": "#1565c0",
    "Center-Left": "#42a5f5",
    "Center": "#78909c",
    "Center-Right": "#ef9a9a",
    "Right": "#e53935",
    "Far Right": "#b71c1c",
    "Non-Political": "#66bb6a",
}

RELIABILITY_COLORS = {
    "high": "#4caf50",
    "medium": "#ff9800",
    "low": "#f44336",
    "unknown": "#9e9e9e",
}

CONTENT_CATEGORIES = [
    "News & Politics",
    "Technology",
    "Science & Education",
    "Entertainment",
    "Sports",
    "Business & Finance",
    "Health & Wellness",
    "Arts & Culture",
    "Gaming",
    "Opinion & Commentary",
    "Satire",
    "Lifestyle",
]

ECHO_CHAMBER_THRESHOLDS = {
    "low": 30,
    "moderate": 60,
    "high": 80,
}

LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

REDDIT_HEADERS = {
    "User-Agent": "MediaDietDiagnostic/1.0 (hackathon project)",
}


def get_anthropic_api_key() -> str | None:
    return os.getenv("ANTHROPIC_API_KEY")
