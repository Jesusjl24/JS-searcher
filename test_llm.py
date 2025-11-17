from LLM_Scorer import parse_resume_with_llm

# Test with a sample resume text
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
Bachelor of Thuganomics, University of Sydney (2014-2017)
"""

print("Testing Resume Parser...\n")
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