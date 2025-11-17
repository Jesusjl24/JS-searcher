"""
Utility functions for JS-searcher application
Includes URL building, validation, logging setup, and helpers
"""

import logging
import time
import random
import re
from typing import Optional, Dict, List
from urllib.parse import quote, urljoin
from config import (
    SCRAPING_CONFIG,
    WORK_TYPE_MAP,
    REMOTE_MAP,
    DATE_MAP,
    LOGGING_CONFIG,
    SCORE_THRESHOLDS,
    SCORE_COLORS,
)


def setup_logging(log_level: str = None, log_file: str = None) -> None:
    """
    Setup logging configuration for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    """
    level = log_level or LOGGING_CONFIG["level"]
    log_format = LOGGING_CONFIG["format"]

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),  # Console output
        ]
    )

    # Add file handler if specified
    if log_file or LOGGING_CONFIG.get("log_file"):
        file_path = log_file or LOGGING_CONFIG["log_file"]
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

    logging.info("Logging configured successfully")


def sanitize_search_term(search_term: str) -> str:
    """
    Sanitize and format search term for URL

    Args:
        search_term: Raw search term from user

    Returns:
        Sanitized search term safe for URLs
    """
    if not search_term or not search_term.strip():
        raise ValueError("Search term cannot be empty")

    # Remove special characters except spaces and hyphens
    sanitized = re.sub(r'[^\w\s-]', '', search_term)

    # Replace spaces with hyphens
    sanitized = re.sub(r'\s+', '-', sanitized.strip())

    # Convert to lowercase
    sanitized = sanitized.lower()

    # Remove consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')

    if not sanitized:
        raise ValueError("Search term contains no valid characters")

    logging.debug(f"Sanitized '{search_term}' to '{sanitized}'")
    return sanitized


def sanitize_location(location: str) -> str:
    """
    Sanitize and format location for URL

    Args:
        location: Raw location from user

    Returns:
        Sanitized location safe for URLs
    """
    if not location or not location.strip():
        raise ValueError("Location cannot be empty")

    # Similar sanitization as search term
    sanitized = re.sub(r'[^\w\s-]', '', location)
    sanitized = re.sub(r'\s+', '-', sanitized.strip())
    sanitized = sanitized.lower()
    sanitized = re.sub(r'-+', '-', sanitized)
    sanitized = sanitized.strip('-')

    if not sanitized:
        raise ValueError("Location contains no valid characters")

    logging.debug(f"Sanitized location '{location}' to '{sanitized}'")
    return sanitized


def build_seek_url(
    search_term: str,
    location: str,
    work_type: Optional[str] = None,
    remote_option: Optional[str] = None,
    salary_min: Optional[int] = None,
    date_posted: Optional[str] = None,
    page: int = 1
) -> str:
    """
    Build SEEK URL with filters

    Args:
        search_term: Job title to search for
        location: Location to search in
        work_type: Employment type filter
        remote_option: Remote work filter
        salary_min: Minimum salary filter
        date_posted: Date posted filter
        page: Page number for pagination

    Returns:
        Complete SEEK URL with filters
    """
    # Sanitize inputs
    formatted_search = sanitize_search_term(search_term)
    formatted_location = sanitize_location(location)

    # Build base URL
    base_url = SCRAPING_CONFIG["base_url"]
    search_url = f"{base_url}/{formatted_search}-jobs/in-{formatted_location}"

    # Build query parameters
    params = []

    # Work type filter
    if work_type and work_type.lower() in WORK_TYPE_MAP:
        params.append(WORK_TYPE_MAP[work_type.lower()])

    # Remote option filter
    if remote_option and remote_option.lower() in REMOTE_MAP:
        params.append(REMOTE_MAP[remote_option.lower()])

    # Salary filter
    if salary_min and isinstance(salary_min, int) and salary_min > 0:
        params.append(f"salarytype=annual&salaryrange={salary_min}-")

    # Date posted filter
    if date_posted:
        if date_posted.lower() == "today":
            params.append("daterange=1")
        elif date_posted.isdigit():
            params.append(f"daterange={date_posted}")

    # Pagination
    if page > 1:
        params.append(f"page={page}")

    # Combine URL with parameters
    if params:
        search_url += "?" + "&".join(params)

    logging.info(f"Built URL: {search_url}")
    return search_url


def random_delay(min_seconds: float = None, max_seconds: float = None) -> None:
    """
    Add a random delay to avoid rate limiting

    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    min_delay = min_seconds or SCRAPING_CONFIG["request_delay_min"]
    max_delay = max_seconds or SCRAPING_CONFIG["request_delay_max"]

    delay = random.uniform(min_delay, max_delay)
    logging.debug(f"Waiting {delay:.2f} seconds...")
    time.sleep(delay)


def validate_max_jobs(max_jobs: int) -> int:
    """
    Validate and constrain max_jobs parameter

    Args:
        max_jobs: Requested maximum number of jobs

    Returns:
        Validated max_jobs value

    Raises:
        ValueError: If max_jobs is invalid
    """
    if not isinstance(max_jobs, int):
        raise ValueError(f"max_jobs must be an integer, got {type(max_jobs)}")

    if max_jobs < 1:
        raise ValueError("max_jobs must be at least 1")

    if max_jobs > SCRAPING_CONFIG["max_jobs_limit"]:
        logging.warning(
            f"max_jobs ({max_jobs}) exceeds limit ({SCRAPING_CONFIG['max_jobs_limit']}), "
            f"using limit instead"
        )
        return SCRAPING_CONFIG["max_jobs_limit"]

    return max_jobs


def get_score_color(score: int) -> str:
    """
    Get color emoji for match score

    Args:
        score: Match score (0-100)

    Returns:
        Color emoji
    """
    if score >= SCORE_THRESHOLDS["strong_match"]:
        return SCORE_COLORS["strong"]
    elif score >= SCORE_THRESHOLDS["good_match"]:
        return SCORE_COLORS["good"]
    elif score >= SCORE_THRESHOLDS["moderate_match"]:
        return SCORE_COLORS["moderate"]
    else:
        return SCORE_COLORS["weak"]


def get_recommendation_from_score(score: int) -> str:
    """
    Get recommendation text based on score

    Args:
        score: Match score (0-100)

    Returns:
        Recommendation text
    """
    if score >= SCORE_THRESHOLDS["strong_match"]:
        return "Strong Match"
    elif score >= SCORE_THRESHOLDS["good_match"]:
        return "Good Match"
    elif score >= SCORE_THRESHOLDS["moderate_match"]:
        return "Moderate Match"
    else:
        return "Weak Match"


def parse_salary_filter(salary_str: str) -> Optional[int]:
    """
    Parse salary filter string to integer

    Args:
        salary_str: Salary string like "80K+" or "Any"

    Returns:
        Salary as integer or None
    """
    if not salary_str or salary_str == "Any":
        return None

    try:
        # Remove "K+" and convert to full number
        salary_num = int(salary_str.replace("K+", "")) * 1000
        return salary_num
    except (ValueError, AttributeError):
        logging.warning(f"Could not parse salary: {salary_str}")
        return None


def format_active_filters(
    work_type: str,
    remote_option: str,
    salary_filter: str,
    date_posted: str
) -> List[str]:
    """
    Format active filters for display

    Args:
        work_type: Selected work type
        remote_option: Selected remote option
        salary_filter: Selected salary filter
        date_posted: Selected date filter

    Returns:
        List of formatted filter strings
    """
    active_filters = []

    if work_type and work_type != "Any":
        active_filters.append(f"📋 {work_type}")

    if remote_option and remote_option != "Any":
        active_filters.append(f"🏠 {remote_option}")

    if salary_filter and salary_filter != "Any":
        active_filters.append(f"💰 {salary_filter}")

    if date_posted and date_posted != "Any time":
        active_filters.append(f"📅 {date_posted}")

    return active_filters


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and special characters

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Replace multiple spaces/newlines with single space
    cleaned = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    return cleaned


def is_valid_url(url: str) -> bool:
    """
    Validate URL format

    Args:
        url: URL to validate

    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_pattern.match(url) is not None
