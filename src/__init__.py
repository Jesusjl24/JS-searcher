"""
JS-searcher - Job Search Application
Source package containing core functionality
"""

__version__ = "2.0.0"
__author__ = "JS-searcher Team"

from src.scraper import scrape_seek_jobs, JobScraper
from src.llm_scorer import parse_resume_with_llm, score_job_match
from src.file_handlers import extract_text_from_resume

__all__ = [
    "scrape_seek_jobs",
    "JobScraper",
    "parse_resume_with_llm",
    "score_job_match",
    "extract_text_from_resume",
]
