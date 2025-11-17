"""
Unit tests for utility functions
"""

import pytest
from src.utils import (
    sanitize_search_term,
    sanitize_location,
    build_seek_url,
    validate_max_jobs,
    get_score_color,
    get_recommendation_from_score,
    parse_salary_filter,
    format_active_filters,
    truncate_text,
    clean_text,
    is_valid_url,
)


class TestSanitization:
    """Test input sanitization functions"""

    def test_sanitize_search_term_basic(self):
        assert sanitize_search_term("Project Manager") == "project-manager"

    def test_sanitize_search_term_special_chars(self):
        assert sanitize_search_term("C++ Developer!!!") == "c-developer"

    def test_sanitize_search_term_multiple_spaces(self):
        assert sanitize_search_term("Senior   Software    Engineer") == "senior-software-engineer"

    def test_sanitize_search_term_empty_raises(self):
        with pytest.raises(ValueError):
            sanitize_search_term("")

    def test_sanitize_location_basic(self):
        assert sanitize_location("Sydney") == "sydney"

    def test_sanitize_location_multiple_words(self):
        assert sanitize_location("New York") == "new-york"


class TestURLBuilding:
    """Test URL building functions"""

    def test_build_seek_url_basic(self):
        url = build_seek_url("developer", "sydney")
        assert "developer-jobs" in url
        assert "in-sydney" in url

    def test_build_seek_url_with_filters(self):
        url = build_seek_url(
            "developer",
            "sydney",
            work_type="full-time",
            salary_min=80000
        )
        assert "fullTime=true" in url
        assert "salaryrange=80000" in url

    def test_build_seek_url_pagination(self):
        url = build_seek_url("developer", "sydney", page=2)
        assert "page=2" in url


class TestValidation:
    """Test validation functions"""

    def test_validate_max_jobs_valid(self):
        assert validate_max_jobs(5) == 5

    def test_validate_max_jobs_exceeds_limit(self):
        result = validate_max_jobs(1000)
        assert result <= 50  # Assuming limit is 50

    def test_validate_max_jobs_negative_raises(self):
        with pytest.raises(ValueError):
            validate_max_jobs(-1)

    def test_validate_max_jobs_zero_raises(self):
        with pytest.raises(ValueError):
            validate_max_jobs(0)


class TestScoring:
    """Test scoring helper functions"""

    def test_get_score_color_strong(self):
        assert get_score_color(85) == "🟢"

    def test_get_score_color_good(self):
        assert get_score_color(70) == "🟡"

    def test_get_score_color_weak(self):
        assert get_score_color(30) == "🔴"

    def test_get_recommendation_strong(self):
        assert get_recommendation_from_score(85) == "Strong Match"

    def test_get_recommendation_good(self):
        assert get_recommendation_from_score(70) == "Good Match"

    def test_get_recommendation_weak(self):
        assert get_recommendation_from_score(30) == "Weak Match"


class TestParsing:
    """Test parsing functions"""

    def test_parse_salary_filter_valid(self):
        assert parse_salary_filter("80K+") == 80000

    def test_parse_salary_filter_any(self):
        assert parse_salary_filter("Any") is None

    def test_parse_salary_filter_none(self):
        assert parse_salary_filter(None) is None

    def test_format_active_filters(self):
        filters = format_active_filters(
            "Full time",
            "Remote",
            "80K+",
            "Last 7 days"
        )
        assert len(filters) == 4
        assert any("Full time" in f for f in filters)


class TestTextUtils:
    """Test text utility functions"""

    def test_truncate_text_short(self):
        text = "Short text"
        assert truncate_text(text, 100) == text

    def test_truncate_text_long(self):
        text = "A" * 100
        truncated = truncate_text(text, 50)
        assert len(truncated) <= 50

    def test_clean_text(self):
        assert clean_text("  Multiple   spaces  ") == "Multiple spaces"

    def test_clean_text_newlines(self):
        assert clean_text("Line1\n\n\nLine2") == "Line1 Line2"

    def test_is_valid_url_valid(self):
        assert is_valid_url("https://www.seek.com.au") is True

    def test_is_valid_url_invalid(self):
        assert is_valid_url("not a url") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
