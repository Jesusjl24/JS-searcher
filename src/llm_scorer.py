"""
LLM-based resume parsing and job matching using Mistral AI
Handles resume analysis and job scoring with proper error handling
"""

import os
import json
import logging
import time
from typing import Optional, Dict, List
from dotenv import load_dotenv
from mistralai import Mistral

from config import LLM_CONFIG, get_env_variable
from src.utils import truncate_text, clean_text

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class APIKeyNotFoundError(LLMError):
    """Raised when API key is not found"""
    pass


class LLMAPIError(LLMError):
    """Raised when LLM API call fails"""
    pass


class JSONParseError(LLMError):
    """Raised when LLM response cannot be parsed as JSON"""
    pass


def get_mistral_client() -> Mistral:
    """
    Get initialized Mistral client

    Returns:
        Mistral client instance

    Raises:
        APIKeyNotFoundError: If API key is not found
    """
    try:
        api_key = get_env_variable("MISTRAL_API_KEY")
        return Mistral(api_key=api_key)
    except ValueError:
        logger.error("MISTRAL_API_KEY not found in environment variables")
        raise APIKeyNotFoundError(
            "MISTRAL_API_KEY not found in .env file! "
            "Please create a .env file with your Mistral API key."
        )


def remove_markdown_formatting(text: str) -> str:
    """
    Remove markdown code block formatting from LLM response

    Args:
        text: Raw LLM response text

    Returns:
        Cleaned text without markdown formatting
    """
    text = text.strip()

    # Remove markdown code blocks
    if text.startswith("```"):
        # Split by ``` and take the middle part
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]

            # Remove language identifier (e.g., "json")
            if text.startswith("json"):
                text = text[4:]
            elif text.startswith("JSON"):
                text = text[4:]

            text = text.strip()

    return text


def call_mistral_api(
    prompt: str,
    model: str = None,
    max_retries: int = 3,
    timeout: int = None
) -> str:
    """
    Call Mistral API with retry logic

    Args:
        prompt: Prompt to send to the API
        model: Model to use (uses config default if None)
        max_retries: Maximum number of retries
        timeout: API timeout in seconds

    Returns:
        LLM response text

    Raises:
        LLMAPIError: If API call fails after retries
    """
    model = model or LLM_CONFIG["model"]
    timeout = timeout or LLM_CONFIG["timeout"]

    client = get_mistral_client()

    for attempt in range(max_retries):
        try:
            logger.debug(f"Calling Mistral API (attempt {attempt + 1}/{max_retries})")

            response = client.chat.complete(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=LLM_CONFIG.get("temperature", 0.3),
            )

            response_text = response.choices[0].message.content.strip()
            logger.debug(f"Received response: {len(response_text)} characters")

            return response_text

        except Exception as e:
            logger.warning(f"API call failed (attempt {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"API call failed after {max_retries} attempts")
                raise LLMAPIError(f"Mistral API call failed: {str(e)}")


def smart_truncate(text: str, max_chars: int) -> str:
    """
    Truncate text intelligently at sentence boundaries

    Args:
        text: Text to truncate
        max_chars: Maximum number of characters

    Returns:
        Truncated text
    """
    if len(text) <= max_chars:
        return text

    # Try to truncate at sentence boundary
    truncated = text[:max_chars]

    # Find last sentence ending
    for delimiter in ['. ', '.\n', '! ', '?\n']:
        last_sentence = truncated.rfind(delimiter)
        if last_sentence > max_chars * 0.7:  # At least 70% of max length
            return truncated[:last_sentence + 1]

    # Fallback: truncate at word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space] + "..."

    # Last resort: hard truncate
    return truncated + "..."


def parse_resume_with_llm(resume_text: str) -> Optional[Dict]:
    """
    Parse resume text using Mistral LLM to extract structured information

    Args:
        resume_text: Raw resume text

    Returns:
        Dictionary with parsed resume information or None if parsing fails
    """
    logger.info("Parsing resume with Mistral LLM...")

    # Smart truncate resume text
    max_chars = LLM_CONFIG["resume_max_chars"]
    truncated_text = smart_truncate(resume_text, max_chars)

    if len(resume_text) > max_chars:
        logger.warning(f"Resume truncated from {len(resume_text)} to {len(truncated_text)} characters")

    prompt = f"""You are a professional resume parser. Extract key information from this resume and return it in JSON format.

RESUME TEXT:
{truncated_text}

Extract the following information:
1. Skills (technical and soft skills) - be comprehensive
2. Years of experience (estimate based on work history, return as integer)
3. Education (degrees, certifications)
4. Previous job titles
5. Industries worked in
6. Key achievements (notable accomplishments)
7. Preferred role types (infer from experience pattern)
8. Location (if mentioned, otherwise "Unknown")

Return ONLY a valid JSON object with this exact structure (no markdown, no code blocks, just raw JSON):
{{
    "skills": ["skill1", "skill2", "skill3"],
    "experience_years": 5,
    "education": ["degree1", "degree2"],
    "previous_titles": ["title1", "title2"],
    "industries": ["industry1", "industry2"],
    "achievements": ["achievement1", "achievement2"],
    "preferred_roles": ["role1", "role2"],
    "location": "location or Unknown"
}}

CRITICAL: Return ONLY the JSON object. No explanations, no markdown formatting, no code blocks."""

    try:
        # Call Mistral API
        response_text = call_mistral_api(prompt)

        logger.debug(f"Raw LLM response preview: {response_text[:200]}...")

        # Remove markdown formatting
        cleaned_response = remove_markdown_formatting(response_text)

        # Parse JSON
        profile = json.loads(cleaned_response)

        # Validate required fields
        required_fields = ["skills", "experience_years", "education", "previous_titles"]
        for field in required_fields:
            if field not in profile:
                logger.warning(f"Missing required field: {field}")
                profile[field] = [] if field != "experience_years" else 0

        logger.info("✅ Successfully parsed resume!")
        logger.info(f"   Found {len(profile.get('skills', []))} skills")
        logger.info(f"   Experience: {profile.get('experience_years', 0)} years")

        return profile

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response was: {response_text if 'response_text' in locals() else 'N/A'}")
        raise JSONParseError(f"Could not parse LLM response as JSON: {str(e)}")

    except LLMAPIError as e:
        logger.error(f"LLM API error: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error parsing resume: {e}")
        return None


def score_job_match(job_data: Dict, user_profile: Dict) -> Dict:
    """
    Score how well a job matches the user's profile using LLM

    Args:
        job_data: Dictionary with job details
        user_profile: Dictionary with parsed resume data

    Returns:
        Dictionary with match score and analysis
    """
    logger.info(f"Scoring job match for '{job_data.get('title', 'Unknown')}'...")

    # Get job description (prefer full, fallback to short)
    job_description = job_data.get('full_description', job_data.get('short_description', 'N/A'))

    # Smart truncate description
    max_chars = LLM_CONFIG["job_description_max_chars"]
    truncated_desc = smart_truncate(job_description, max_chars)

    # Prepare profile summary
    skills_summary = ', '.join(user_profile.get('skills', [])[:LLM_CONFIG["max_skills_to_show"]])
    titles_summary = ', '.join(user_profile.get('previous_titles', [])[:LLM_CONFIG["max_titles_to_show"]])
    industries_summary = ', '.join(user_profile.get('industries', [])[:LLM_CONFIG["max_industries_to_show"]])
    education_summary = ', '.join(user_profile.get('education', [])[:LLM_CONFIG["max_education_to_show"]])

    prompt = f"""You are an expert career advisor and recruiter. Score how well this job matches the candidate's profile.

CANDIDATE PROFILE:
Skills: {skills_summary}
Experience: {user_profile.get('experience_years', 0)} years
Previous Roles: {titles_summary}
Industries: {industries_summary}
Education: {education_summary}

JOB DETAILS:
Title: {job_data.get('title', 'N/A')}
Company: {job_data.get('company', 'N/A')}
Location: {job_data.get('location', 'N/A')}
Salary: {job_data.get('salary', 'Not specified')}
Description: {truncated_desc}

Analyze the match comprehensively considering:
1. Skill alignment (technical and soft skills)
2. Experience level appropriateness
3. Industry relevance
4. Career progression fit
5. Role responsibilities match

Return ONLY a valid JSON object (no markdown, no code blocks):
{{
    "score": 75,
    "reasoning": "Clear 2-3 sentence explanation of the score",
    "pros": ["specific pro 1", "specific pro 2", "specific pro 3"],
    "cons": ["specific con 1", "specific con 2"],
    "skill_match_percentage": 70,
    "strong_matches": ["specific match 1", "specific match 2"],
    "gaps": ["specific gap 1", "specific gap 2"],
    "recommendation": "Strong Match",
    "strategic_considerations": ["consideration 1", "consideration 2"]
}}

Score scale:
- 80-100: Strong Match - Highly recommended
- 60-79: Good Match - Worth applying
- 40-59: Moderate Match - Consider if interested
- 0-39: Weak Match - Not recommended

Recommendation must be one of: "Strong Match", "Good Match", "Moderate Match", "Weak Match"

CRITICAL: Return ONLY the JSON object."""

    try:
        # Call Mistral API
        response_text = call_mistral_api(prompt)

        # Remove markdown formatting
        cleaned_response = remove_markdown_formatting(response_text)

        # Parse JSON
        match_data = json.loads(cleaned_response)

        # Validate and set defaults
        if "score" not in match_data:
            match_data["score"] = 0

        if "recommendation" not in match_data:
            # Auto-generate based on score
            score = match_data["score"]
            if score >= 80:
                match_data["recommendation"] = "Strong Match"
            elif score >= 60:
                match_data["recommendation"] = "Good Match"
            elif score >= 40:
                match_data["recommendation"] = "Moderate Match"
            else:
                match_data["recommendation"] = "Weak Match"

        # Ensure required fields exist
        defaults = {
            "reasoning": "No reasoning provided",
            "pros": [],
            "cons": [],
            "skill_match_percentage": 0,
            "strong_matches": [],
            "gaps": [],
            "strategic_considerations": []
        }

        for key, default_value in defaults.items():
            if key not in match_data:
                match_data[key] = default_value

        logger.info(f"   ✅ Score: {match_data['score']}/100 - {match_data['recommendation']}")

        return match_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response was: {response_text if 'response_text' in locals() else 'N/A'}")

        # Return default error response
        return {
            "score": 0,
            "reasoning": "Error analyzing match - please review manually",
            "pros": ["Could not analyze automatically"],
            "cons": ["JSON parsing error"],
            "skill_match_percentage": 0,
            "recommendation": "Review Manually",
            "strong_matches": [],
            "gaps": [],
            "strategic_considerations": []
        }

    except LLMAPIError as e:
        logger.error(f"LLM API error: {e}")

        return {
            "score": 0,
            "reasoning": "API error occurred - please try again later",
            "pros": [],
            "cons": ["API connection error"],
            "skill_match_percentage": 0,
            "recommendation": "Review Manually",
            "strong_matches": [],
            "gaps": [],
            "strategic_considerations": []
        }

    except Exception as e:
        logger.error(f"Unexpected error scoring job: {e}")

        return {
            "score": 0,
            "reasoning": "Unexpected error - please review manually",
            "pros": [],
            "cons": ["Analysis error"],
            "skill_match_percentage": 0,
            "recommendation": "Review Manually",
            "strong_matches": [],
            "gaps": [],
            "strategic_considerations": []
        }


if __name__ == "__main__":
    # Setup logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Test with sample resume
    sample_resume = """
John Doe
Sydney, Australia

EXPERIENCE:
Senior Product Manager at TechCorp (2020-2024)
- Led product development for AI-powered applications
- Managed team of 5 developers
- Increased user engagement by 40%

Product Manager at StartupXYZ (2018-2020)
- Built MVP for SaaS platform
- Worked with React and Python

SKILLS:
Python, React, Product Management, Agile, AI/ML, Stakeholder Management

EDUCATION:
Bachelor of Computer Science, University of Sydney (2014-2017)
"""

    print("Testing Resume Parser...\n")
    try:
        profile = parse_resume_with_llm(sample_resume)

        if profile:
            print("\n✅ Parsed Profile:")
            print(f"Skills: {profile.get('skills', [])}")
            print(f"Experience: {profile.get('experience_years')} years")
            print(f"Previous Titles: {profile.get('previous_titles', [])}")
            print(f"Industries: {profile.get('industries', [])}")
            print(f"Education: {profile.get('education', [])}")
        else:
            print("\n❌ Failed to parse resume")

    except Exception as e:
        print(f"\n❌ Error: {e}")
