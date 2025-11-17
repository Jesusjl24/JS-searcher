import os
from dotenv import load_dotenv
from mistralai import Mistral
import json

# Load environment variables
load_dotenv()

# Initialize Mistral client
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("❌ MISTRAL_API_KEY not found in .env file!")

client = Mistral(api_key=api_key)


def extract_text_from_resume(uploaded_file):
    """
    Extract text from uploaded resume file
    Supports: PDF, DOCX, TXT
    """
    file_type = uploaded_file.name.split('.')[-1].lower()

    if file_type == 'txt':
        return uploaded_file.read().decode('utf-8')

    elif file_type == 'pdf':
        import PyPDF2
        import io

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        uploaded_file.seek(0)
        return text

    elif file_type == 'docx':
        import docx
        import io

        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        uploaded_file.seek(0)
        return text

    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def parse_resume_with_llm(resume_text):
    """
    Agent 1: Resume Parser
    Uses Mistral LLM to extract structured information from resume
    """

    print("🤖 Agent 1: Parsing resume with Mistral LLM...")

    prompt = f"""You are a professional resume parser. Extract key information from this resume and return it in JSON format.

RESUME TEXT:
{resume_text[:4000]}

Extract the following information:
1. Skills (technical and soft skills)
2. Years of experience (estimate based on work history)
3. Education
4. Previous job titles
5. Industries worked in
6. Key achievements
7. Preferred role types (infer from experience)
8. Location (if mentioned)

Return ONLY a valid JSON object with this structure (no markdown, no code blocks, just JSON):
{{
    "skills": ["skill1", "skill2", "skill3"],
    "experience_years": number,
    "education": ["degree1", "degree2"],
    "previous_titles": ["title1", "title2"],
    "industries": ["industry1", "industry2"],
    "achievements": ["achievement1", "achievement2"],
    "preferred_roles": ["role1", "role2"],
    "location": "location or Unknown"
}}

CRITICAL: Return ONLY the JSON object. No explanations, no markdown, no code blocks."""

    response_text = None  # Initialize before try block

    try:
        # Call Mistral API
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the response
        response_text = response.choices[0].message.content.strip()

        print(f"📝 Raw LLM response: {response_text[:200]}...")

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        # Parse JSON
        profile = json.loads(response_text)

        print("✅ Agent 1: Successfully parsed resume!")
        print(f"   Found {len(profile.get('skills', []))} skills")
        print(f"   Experience: {profile.get('experience_years', 0)} years")

        return profile

    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        if response_text:
            print(f"Response was: {response_text}")
        return None
    except Exception as e:
        print(f"❌ Error calling Mistral API: {e}")
        if response_text:
            print(f"Response was: {response_text}")
        return None


def score_job_match(job_data, user_profile):
    """
    Agent 2: Job Matcher
    Scores how well a job matches the user's profile
    """

    print(f"🤖 Agent 2: Scoring job '{job_data['title']}'...")

    prompt = f"""You are an expert career advisor. Score how well this job matches the candidate's profile.

CANDIDATE PROFILE:
Skills: {', '.join(user_profile.get('skills', [])[:15])}
Experience: {user_profile.get('experience_years', 0)} years
Previous Roles: {', '.join(user_profile.get('previous_titles', [])[:5])}
Industries: {', '.join(user_profile.get('industries', [])[:3])}
Education: {', '.join(user_profile.get('education', [])[:2])}

JOB DETAILS:
Title: {job_data['title']}
Company: {job_data['company']}
Location: {job_data['location']}
Salary: {job_data['salary']}
Description: {job_data.get('full_description', job_data.get('short_description', 'N/A'))[:1500]}

Analyze the match and return ONLY a valid JSON object (no markdown, no code blocks):
{{
    "score": number between 0-100,
    "reasoning": "2-3 sentence explanation of why this score",
    "pros": ["pro1", "pro2", "pro3"],
    "cons": ["con1", "con2"],
    "skill_match_percentage": number between 0-100,
    "recommendation": "Strong Match" or "Good Match" or "Moderate Match" or "Weak Match"
}}

CRITICAL: Return ONLY the JSON object."""

    response_text = None  # Initialize before try block

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        match_data = json.loads(response_text)

        print(f"   ✅ Score: {match_data['score']}/100 - {match_data['recommendation']}")

        return match_data

    except Exception as e:
        print(f"   ❌ Error scoring job: {e}")
        if response_text:
            print(f"Response was: {response_text}")
        return {
            "score": 0,
            "reasoning": "Error analyzing match",
            "pros": [],
            "cons": ["Could not analyze"],
            "skill_match_percentage": 0,
            "recommendation": "Review Manually"
        }