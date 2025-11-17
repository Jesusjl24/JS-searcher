"""
Unit tests for LLM scorer
Improved version with proper mocking
"""

import pytest
from unittest.mock import Mock, patch
from src.llm_scorer import (
    remove_markdown_formatting,
    smart_truncate,
    get_mistral_client,
    APIKeyNotFoundError,
)


class TestMarkdownRemoval:
    """Test markdown formatting removal"""

    def test_remove_markdown_simple(self):
        text = '```json\n{"key": "value"}\n```'
        result = remove_markdown_formatting(text)
        assert result == '{"key": "value"}'

    def test_remove_markdown_no_formatting(self):
        text = '{"key": "value"}'
        result = remove_markdown_formatting(text)
        assert result == '{"key": "value"}'

    def test_remove_markdown_uppercase_json(self):
        text = '```JSON\n{"key": "value"}\n```'
        result = remove_markdown_formatting(text)
        assert result == '{"key": "value"}'


class TestSmartTruncate:
    """Test smart text truncation"""

    def test_smart_truncate_short_text(self):
        text = "Short text"
        result = smart_truncate(text, 100)
        assert result == text

    def test_smart_truncate_at_sentence(self):
        text = "First sentence. Second sentence. Third sentence."
        result = smart_truncate(text, 30)
        assert result.endswith(".")
        assert len(result) <= 30

    def test_smart_truncate_long_no_sentences(self):
        text = "A" * 100
        result = smart_truncate(text, 50)
        assert len(result) <= 53  # 50 + "..."


class TestAPIKeyHandling:
    """Test API key handling"""

    @patch.dict('os.environ', {}, clear=True)
    def test_get_mistral_client_no_key_raises(self):
        with pytest.raises(APIKeyNotFoundError):
            get_mistral_client()

    @patch.dict('os.environ', {'MISTRAL_API_KEY': 'test-key'})
    def test_get_mistral_client_with_key(self):
        # Should not raise
        client = get_mistral_client()
        assert client is not None


class TestResumeParser:
    """Test resume parsing (requires mocking)"""

    @patch('src.llm_scorer.call_mistral_api')
    def test_parse_resume_success(self, mock_api):
        # Mock API response
        mock_api.return_value = '''
        {
            "skills": ["Python", "Project Management"],
            "experience_years": 5,
            "education": ["Bachelor of Science"],
            "previous_titles": ["Project Manager"],
            "industries": ["Tech"],
            "achievements": ["Led team of 5"],
            "preferred_roles": ["Project Manager"],
            "location": "Sydney"
        }
        '''

        from src.llm_scorer import parse_resume_with_llm

        sample_resume = "John Doe\nProject Manager with 5 years experience"
        result = parse_resume_with_llm(sample_resume)

        assert result is not None
        assert "skills" in result
        assert result["experience_years"] == 5


class TestJobMatcher:
    """Test job matching (requires mocking)"""

    @patch('src.llm_scorer.call_mistral_api')
    def test_score_job_match_success(self, mock_api):
        # Mock API response
        mock_api.return_value = '''
        {
            "score": 75,
            "reasoning": "Good match based on skills",
            "pros": ["Skill match", "Experience match"],
            "cons": ["Location difference"],
            "skill_match_percentage": 80,
            "recommendation": "Good Match",
            "strong_matches": ["Python", "Management"],
            "gaps": ["AWS experience"],
            "strategic_considerations": ["Consider relocation"]
        }
        '''

        from src.llm_scorer import score_job_match

        job_data = {
            "title": "Project Manager",
            "company": "TechCorp",
            "location": "Sydney",
            "salary": "100K-120K",
            "full_description": "Looking for PM with Python skills"
        }

        user_profile = {
            "skills": ["Python", "Management"],
            "experience_years": 5,
            "previous_titles": ["Project Manager"],
            "industries": ["Tech"],
            "education": ["Bachelor"]
        }

        result = score_job_match(job_data, user_profile)

        assert result is not None
        assert result["score"] == 75
        assert result["recommendation"] == "Good Match"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
