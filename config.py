"""
Configuration file for JS-searcher application
Contains all constants, settings, and configuration options
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# File paths
JOBS_CSV_PATH = DATA_DIR / "jobs.csv"

# Scraping configuration
SCRAPING_CONFIG = {
    "base_url": "https://www.seek.com.au",
    "max_jobs_limit": 50,
    "default_max_jobs": 5,
    "page_load_timeout": 30,  # seconds
    "element_wait_timeout": 10,  # seconds
    "request_delay_min": 2,  # seconds between requests
    "request_delay_max": 4,  # seconds between requests
    "max_retries": 3,
    "retry_delay": 2,  # seconds
}

# Selenium configuration
SELENIUM_CONFIG = {
    "headless": True,
    "disable_gpu": True,
    "no_sandbox": True,
    "disable_dev_shm": True,
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "window_size": "1920,1080",
}

# LLM configuration
LLM_CONFIG = {
    "model": "mistral-small-latest",
    "resume_max_chars": 5000,  # Increased from 4000
    "job_description_max_chars": 2000,  # Increased from 1500
    "max_skills_to_show": 15,
    "max_titles_to_show": 5,
    "max_industries_to_show": 3,
    "max_education_to_show": 2,
    "temperature": 0.3,  # Low temperature for consistent structured output
    "timeout": 30,  # API timeout in seconds
}

# Resume upload configuration
RESUME_CONFIG = {
    "max_file_size_mb": 10,
    "allowed_extensions": ["pdf", "docx", "txt"],
    "max_file_size_bytes": 10 * 1024 * 1024,  # 10MB
}

# UI configuration
UI_CONFIG = {
    "page_title": "Seek.com Job Searcher",
    "page_icon": "🔍",
    "layout": "wide",
    "job_card_columns": [3, 1],  # Main content vs side button
    "resume_modal_max_width": 900,
    "resume_preview_height": 700,
    "text_area_height": 600,
}

# Filter options
WORK_TYPE_OPTIONS = ["Any", "Full time", "Part time", "Contract/Temp", "Casual/Vacation"]
REMOTE_OPTIONS = ["Any", "On-site", "Hybrid", "Remote"]
SALARY_OPTIONS = [
    "Any",
    "30K+", "40K+", "50K+", "60K+", "70K+", "80K+",
    "100K+", "120K+", "150K+", "200K+", "250K+", "350K+"
]
DATE_OPTIONS = ["Any time", "Today", "Last 3 days", "Last 7 days", "Last 14 days", "Last 30 days"]

# Filter mappings for SEEK URL parameters
WORK_TYPE_MAP = {
    "full-time": "fullTime=true",
    "part-time": "partTime=true",
    "contract-temp": "contract=true",
    "casual-vacation": "casual=true"
}

REMOTE_MAP = {
    "remote": "worktype=work-from-home",
    "hybrid": "worktype=hybrid",
    "on-site": "worktype=office"
}

DATE_MAP = {
    "Today": "today",
    "Last 3 days": "3",
    "Last 7 days": "7",
    "Last 14 days": "14",
    "Last 30 days": "30"
}

# Job matching score thresholds
SCORE_THRESHOLDS = {
    "strong_match": 80,
    "good_match": 60,
    "moderate_match": 40,
}

# Score colors and icons
SCORE_COLORS = {
    "strong": "🟢",
    "good": "🟡",
    "moderate": "🟠",
    "weak": "🔴",
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_file": BASE_DIR / "app.log",
}

# Environment variables
def get_env_variable(var_name: str, default: str = None) -> str:
    """
    Get environment variable with optional default

    Args:
        var_name: Name of the environment variable
        default: Default value if not found

    Returns:
        Value of the environment variable

    Raises:
        ValueError: If variable not found and no default provided
    """
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable {var_name} not found and no default provided")
    return value
