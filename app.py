"""
Streamlit application for SEEK job search with AI-powered resume matching
Refactored for better modularity and maintainability
"""

import streamlit as st
import pandas as pd
import os
import base64
import logging
from streamlit_modal import Modal

# Import from our modules
from config import (
    UI_CONFIG,
    WORK_TYPE_OPTIONS,
    REMOTE_OPTIONS,
    SALARY_OPTIONS,
    DATE_OPTIONS,
    JOBS_CSV_PATH,
    RESUME_CONFIG,
)
from src.scraper import scrape_seek_jobs_selenium
from src.llm_scorer import parse_resume_with_llm, score_job_match
from src.file_handlers import (
    extract_text_from_resume,
    get_file_info,
    UnsupportedFileTypeError,
    FileSizeExceededError,
    FileReadError,
)
from src.utils import (
    parse_salary_filter,
    format_active_filters,
    get_score_color,
    setup_logging,
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    page_icon=UI_CONFIG["page_icon"],
    layout=UI_CONFIG["layout"]
)

# Title and description
st.title(f"{UI_CONFIG['page_icon']} Seek.com Job searcher")
st.markdown("Find the roles you would like to apply to.")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clear_job_scores():
    """Clear all cached job scores from session state"""
    keys_to_remove = [key for key in st.session_state.keys() if key.startswith('score_')]
    for key in keys_to_remove:
        del st.session_state[key]
    logger.info(f"Cleared {len(keys_to_remove)} cached job scores")


def render_resume_preview(uploaded_file):
    """
    Render resume preview modal

    Args:
        uploaded_file: Streamlit UploadedFile object
    """
    file_info = get_file_info(uploaded_file)
    file_extension = file_info["extension"].lower()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filename", uploaded_file.name)
    with col2:
        st.metric("Size", f"{file_info['size_kb']:.1f} KB")
    with col3:
        st.metric("Type", file_extension.upper())

    st.markdown("---")

    if file_extension == 'pdf':
        try:
            base64_pdf = base64.b64encode(uploaded_file.read()).decode('utf-8')
            uploaded_file.seek(0)

            pdf_display = f'''
                <iframe
                    src="data:application/pdf;base64,{base64_pdf}"
                    width="100%"
                    height="{UI_CONFIG["resume_preview_height"]}px"
                    type="application/pdf"
                    style="border: 2px solid #ddd; border-radius: 8px;"
                >
                </iframe>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error displaying PDF: {e}")

    elif file_extension == 'txt':
        try:
            text_content = uploaded_file.read().decode('utf-8')
            uploaded_file.seek(0)

            st.text_area(
                "Resume Content",
                text_content,
                height=UI_CONFIG["text_area_height"],
                disabled=True,
                label_visibility="collapsed"
            )
        except Exception as e:
            st.error(f"Error reading text file: {e}")

    elif file_extension == 'docx':
        st.info("📝 DOCX Preview - Showing text content")

        try:
            import docx
            import io

            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            uploaded_file.seek(0)

            text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            st.text_area(
                "Resume Content",
                text_content,
                height=UI_CONFIG["text_area_height"],
                disabled=True,
                label_visibility="collapsed"
            )
        except Exception as e:
            st.error(f"Error reading DOCX: {e}")
            st.info("💡 Install python-docx: `pip install python-docx`")


def process_resume(uploaded_file):
    """
    Process uploaded resume and store profile in session state

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        True if successful, False otherwise
    """
    # Check if already processed
    if st.session_state.get('resume_name') == uploaded_file.name and 'resume_profile' in st.session_state:
        return True

    try:
        with st.spinner("🤖 Analyzing your resume with AI..."):
            # Extract text from resume
            resume_text = extract_text_from_resume(uploaded_file)

            # Parse with LLM
            profile = parse_resume_with_llm(resume_text)

            if profile:
                st.session_state['resume_profile'] = profile
                st.session_state['resume_name'] = uploaded_file.name
                st.sidebar.success("🤖 Resume analyzed!")
                logger.info(f"Successfully processed resume: {uploaded_file.name}")
                return True
            else:
                st.sidebar.error("❌ Could not parse resume")
                st.session_state['resume_profile'] = None
                logger.error("Resume parsing returned None")
                return False

    except (UnsupportedFileTypeError, FileSizeExceededError, FileReadError) as e:
        st.sidebar.error(f"❌ {str(e)}")
        st.session_state['resume_profile'] = None
        logger.error(f"File handler error: {e}")
        return False

    except Exception as e:
        st.sidebar.error(f"❌ Error parsing resume: {e}")
        st.session_state['resume_profile'] = None
        logger.error(f"Unexpected error processing resume: {e}")
        return False


def render_job_card(row, idx, uploaded_resume):
    """
    Render a single job card with optional AI matching

    Args:
        row: DataFrame row with job data
        idx: Row index
        uploaded_resume: Uploaded resume file (or None)
    """
    # Calculate match score if resume is uploaded
    match_score = None
    if uploaded_resume and st.session_state.get('resume_profile'):
        cache_key = f"score_{idx}_{row['title']}"

        if cache_key not in st.session_state:
            with st.spinner(f"🤖 Analyzing match for {row['title']}..."):
                try:
                    match_score = score_job_match(row.to_dict(), st.session_state['resume_profile'])
                    st.session_state[cache_key] = match_score
                    logger.info(f"Scored job {idx}: {match_score['score']}/100")
                except Exception as e:
                    logger.error(f"Error scoring job {idx}: {e}")
                    match_score = None
        else:
            match_score = st.session_state[cache_key]

    # Render job card
    with st.container():
        col_main, col_side = st.columns(UI_CONFIG["job_card_columns"])

        with col_main:
            # Job title with match score
            if match_score:
                score = match_score['score']
                color = get_score_color(score)
                st.markdown(f"### {color} [{row['title']}]({row['url']}) - **{score}% Match**")

                # Recommendation badge
                rec = match_score['recommendation']
                if rec == "Strong Match":
                    st.success(f"✨ {rec}")
                elif rec == "Good Match":
                    st.info(f"👍 {rec}")
                else:
                    st.warning(f"🤔 {rec}")
            else:
                st.markdown(f"### [{row['title']}]({row['url']})")

            # Company and location
            st.markdown(f"**🏢 {row['company']}** • 📍 {row['location']}")

            # Salary
            if row['salary'] != 'Not specified':
                st.markdown(f"💰 **{row['salary']}**")
            else:
                st.markdown(f"💰 {row['salary']}")

            # AI Match Analysis
            if match_score:
                with st.expander("🤖 AI Match Analysis", expanded=False):
                    st.markdown(f"**Reasoning:** {match_score['reasoning']}")
                    st.markdown("---")

                    # Pros and Cons
                    col_pros, col_cons = st.columns(2)
                    with col_pros:
                        st.markdown("**✅ Pros:**")
                        for pro in match_score.get('pros', []):
                            st.markdown(f"- {pro}")
                    with col_cons:
                        st.markdown("**⚠️ Cons:**")
                        for con in match_score.get('cons', []):
                            st.markdown(f"- {con}")

                    st.markdown("---")

                    # Strong Matches
                    if match_score.get('strong_matches'):
                        st.markdown(f"**🎯 Strong Matches:** ({match_score.get('skill_match_percentage', 0)}% skill match)")
                        for match in match_score['strong_matches']:
                            st.markdown(f"✅ {match}")

                    # Gaps
                    if match_score.get('gaps'):
                        st.markdown("**⚠️ Gaps:**")
                        for gap in match_score['gaps']:
                            st.markdown(f"⚠️ {gap}")

                    # Strategic Considerations
                    if match_score.get('strategic_considerations'):
                        st.markdown("---")
                        st.markdown("**💡 Strategic Considerations:**")
                        for idx_strat, consideration in enumerate(match_score['strategic_considerations'], 1):
                            st.markdown(f"{idx_strat}. {consideration}")

            # Description
            if row['full_description'] not in ['N/A', 'Description not available', 'Error fetching description']:
                with st.expander("📄 View Full Description"):
                    st.write(row['full_description'])
            elif row['short_description'] != 'N/A':
                with st.expander("📄 View Short Description"):
                    st.write(row['short_description'])

        with col_side:
            st.link_button("Apply Now", row['url'], use_container_width=True)

        st.markdown("---")


# ============================================================================
# SIDEBAR - SEARCH PARAMETERS
# ============================================================================

st.sidebar.header("🎯 Search Parameters")

# Search inputs
search_term = st.sidebar.text_input(
    "Job Title",
    value="Project Manager",
    help="Enter the job title you're looking for"
)

location = st.sidebar.text_input(
    "Location",
    value="Sydney",
    help="Enter the location (e.g., Sydney, Melbourne, Brisbane)"
)

# Advanced Filters
st.sidebar.markdown("---")
st.sidebar.header("🔍 Advanced Filters")

work_type = st.sidebar.selectbox(
    "Work Type",
    WORK_TYPE_OPTIONS,
    help="Filter by employment type"
)

remote_option = st.sidebar.selectbox(
    "Work Location",
    REMOTE_OPTIONS,
    help="Filter by work location preference"
)

salary_filter = st.sidebar.selectbox(
    "Minimum Salary (AUD)",
    SALARY_OPTIONS,
    help="Filter by minimum annual salary"
)

date_posted = st.sidebar.selectbox(
    "Date Posted",
    DATE_OPTIONS,
    help="Filter by when the job was posted"
)

max_jobs = st.sidebar.slider(
    "Number of Jobs",
    min_value=1,
    max_value=RESUME_CONFIG["max_file_size_mb"],
    value=5,
    help="Limit to 5 jobs to avoid IP issues"
)

# Resume upload section
st.sidebar.markdown("---")
st.sidebar.header("📄 Your Resume")

uploaded_resume = st.sidebar.file_uploader(
    "Upload your resume (optional)",
    type=RESUME_CONFIG["allowed_extensions"],
    help="Upload your resume for AI-powered job matching"
)

# Resume upload feedback
if uploaded_resume:
    file_info = get_file_info(uploaded_resume)

    if file_info["within_size_limit"] and file_info["is_valid"]:
        st.sidebar.success(f"✅ {uploaded_resume.name}")
        st.sidebar.caption(f"Size: {file_info['size_kb']:.1f} KB")

        if st.sidebar.button("👁️ Preview Resume", use_container_width=True):
            st.session_state['show_modal'] = True

        # Process resume
        process_resume(uploaded_resume)
    else:
        if not file_info["within_size_limit"]:
            st.sidebar.error(f"❌ File too large (max {RESUME_CONFIG['max_file_size_mb']} MB)")
        if not file_info["is_valid"]:
            st.sidebar.error(f"❌ Invalid file type")
else:
    st.sidebar.info("💡 Upload resume to get AI match scores")

# Search button
search_button = st.sidebar.button("🚀 Search Jobs", type="primary", use_container_width=True)

# Info box
st.sidebar.info("⚠️ Limited to avoid overwhelming SEEK's servers and potential IP bans.")

# ============================================================================
# RESUME PREVIEW MODAL
# ============================================================================

if uploaded_resume and st.session_state.get('show_modal', False):
    modal = Modal(
        "📄 Resume Preview",
        key="resume_modal",
        max_width=UI_CONFIG["resume_modal_max_width"]
    )

    with modal.container():
        render_resume_preview(uploaded_file=uploaded_resume)

        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✖️ Close", use_container_width=True, type="primary"):
                st.session_state['show_modal'] = False
                st.rerun()

# ============================================================================
# MAIN CONTENT - JOB SEARCH
# ============================================================================

if search_button:
    if not search_term:
        st.error("❌ Please enter a job title!")
    else:
        # Clear old job scores
        clear_job_scores()

        # Process filters
        work_type_param = None if work_type == "Any" else work_type.replace("/", "-").lower()
        remote_param = None if remote_option == "Any" else remote_option.lower()
        salary_param = parse_salary_filter(salary_filter)

        # Date filter mapping
        date_param = None
        if date_posted != "Any time":
            date_map = {
                "Today": "today",
                "Last 3 days": "3",
                "Last 7 days": "7",
                "Last 14 days": "14",
                "Last 30 days": "30"
            }
            date_param = date_map.get(date_posted)

        # Show active filters
        active_filters = format_active_filters(
            work_type, remote_option, salary_filter, date_posted
        )

        if active_filters:
            st.info("**Active Filters:** " + " • ".join(active_filters))

        # Show loading spinner
        with st.spinner(f"🔎 Scraping SEEK for '{search_term}' jobs in {location}..."):
            try:
                # Run the scraper
                scrape_seek_jobs_selenium(
                    search_term,
                    location,
                    max_jobs,
                    work_type=work_type_param,
                    remote_option=remote_param,
                    salary_min=salary_param,
                    date_posted=date_param
                )

                # Load the CSV file
                if os.path.exists(JOBS_CSV_PATH):
                    df = pd.read_csv(JOBS_CSV_PATH)

                    st.success(f"✅ Found {len(df)} jobs!")

                    # Display metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Jobs", len(df))
                    with col2:
                        jobs_with_salary = df[df['salary'] != 'Not specified'].shape[0]
                        st.metric("Jobs with Salary", jobs_with_salary)
                    with col3:
                        unique_companies = df['company'].nunique()
                        st.metric("Unique Companies", unique_companies)

                    st.markdown("---")

                    # Display job listings
                    st.subheader("📋 Job Listings")

                    for idx, row in df.iterrows():
                        render_job_card(row, idx, uploaded_resume)

                    # Download button
                    st.download_button(
                        label="📥 Download as CSV",
                        data=df.to_csv(index=False).encode('utf-8'),
                        file_name=f"{search_term.replace(' ', '_')}_jobs.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                else:
                    st.error("❌ No jobs file found. Please try searching again.")

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                logger.error(f"Search error: {e}", exc_info=True)
                st.exception(e)

else:
    # Welcome screen
    st.info("👈 Enter your search criteria in the sidebar and click 'Search Jobs' to get started!")

    # Show previous results if available
    if os.path.exists(JOBS_CSV_PATH):
        st.subheader("📊 Previous Search Results")
        try:
            df = pd.read_csv(JOBS_CSV_PATH)
            st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not load previous results: {e}")
            logger.error(f"Error loading previous results: {e}")
