import streamlit as st
import pandas as pd
from scraper import scrape_seek_jobs_selenium
from streamlit_modal import Modal
import os
import base64

# Page configuration
st.set_page_config(
    page_title="Seek.com Job Searcher",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 Seek.com Job searcher")
st.markdown("Find the roles you would like to apply to.")

# Sidebar for search parameters
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

# NEW: Advanced Filters Section
st.sidebar.markdown("---")
st.sidebar.header("🔍 Advanced Filters")

# Work Type Filter
work_type_options = ["Any", "Full time", "Part time", "Contract/Temp", "Casual/Vacation"]
work_type = st.sidebar.selectbox(
    "Work Type",
    work_type_options,
    help="Filter by employment type"
)

# Remote Options Filter
remote_options = ["Any", "On-site", "Hybrid", "Remote"]
remote_option = st.sidebar.selectbox(
    "Work Location",
    remote_options,
    help="Filter by work location preference"
)

# Salary Filter
salary_options = [
    "Any",
    "30K+", "40K+", "50K+", "60K+", "70K+", "80K+",
    "100K+", "120K+", "150K+", "200K+", "250K+", "350K+"
]
salary_filter = st.sidebar.selectbox(
    "Minimum Salary (AUD)",
    salary_options,
    help="Filter by minimum annual salary"
)

# Date Posted Filter
date_options = ["Any time", "Today", "Last 3 days", "Last 7 days", "Last 14 days", "Last 30 days"]
date_posted = st.sidebar.selectbox(
    "Date Posted",
    date_options,
    help="Filter by when the job was posted"
)

max_jobs = st.sidebar.slider(
    "Number of Jobs",
    min_value=1,
    max_value=5,
    value=5,
    help="Limit to 5 jobs to avoid IP issues"
)

# Resume upload section
st.sidebar.markdown("---")
st.sidebar.header("📄 Your Resume")

uploaded_resume = st.sidebar.file_uploader(
    "Upload your resume (optional)",
    type=['pdf', 'docx', 'txt'],
    help="Upload your resume for AI-powered job matching"
)

if uploaded_resume:
    st.sidebar.success(f"✅ {uploaded_resume.name}")
    file_size = uploaded_resume.size / 1024
    st.sidebar.caption(f"Size: {file_size:.1f} KB")

    if st.sidebar.button("👁️ Preview Resume", width="stretch"):
        st.session_state['show_modal'] = True
else:
    st.sidebar.info("💡 Upload resume to get AI match scores")

# Parse resume with LLM if uploaded
if uploaded_resume:
    if 'resume_profile' not in st.session_state or st.session_state.get('resume_name') != uploaded_resume.name:
        with st.spinner("🤖 Analyzing your resume with AI..."):
            try:
                from LLM_Scorer import extract_text_from_resume, parse_resume_with_llm

                resume_text = extract_text_from_resume(uploaded_resume)
                profile = parse_resume_with_llm(resume_text)

                if profile:
                    st.session_state['resume_profile'] = profile
                    st.session_state['resume_name'] = uploaded_resume.name
                    st.sidebar.success("🤖 Resume analyzed!")
                else:
                    st.sidebar.error("❌ Could not parse resume")
                    st.session_state['resume_profile'] = None
            except Exception as e:
                st.sidebar.error(f"❌ Error parsing resume: {e}")
                st.session_state['resume_profile'] = None

# Search button
search_button = st.sidebar.button("🚀 Search Jobs", type="primary", width="stretch")

# Info box
st.sidebar.info("⚠️ Limited to 5 jobs to be respectful to SEEK's servers and avoid IP bans.")

# Modal for resume preview
if uploaded_resume and st.session_state.get('show_modal', False):
    modal = Modal("📄 Resume Preview", key="resume_modal", max_width=900)

    with modal.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Filename", uploaded_resume.name)
        with col2:
            st.metric("Size", f"{uploaded_resume.size / 1024:.1f} KB")
        with col3:
            file_type = uploaded_resume.name.split('.')[-1].upper()
            st.metric("Type", file_type)

        st.markdown("---")

        file_extension = uploaded_resume.name.split('.')[-1].lower()

        if file_extension == 'pdf':
            base64_pdf = base64.b64encode(uploaded_resume.read()).decode('utf-8')
            uploaded_resume.seek(0)

            pdf_display = f'''
                <iframe 
                    src="data:application/pdf;base64,{base64_pdf}" 
                    width="100%" 
                    height="700px" 
                    type="application/pdf"
                    style="border: 2px solid #ddd; border-radius: 8px;"
                >
                </iframe>
            '''
            st.markdown(pdf_display, unsafe_allow_html=True)

        elif file_extension == 'txt':
            text_content = uploaded_resume.read().decode('utf-8')
            uploaded_resume.seek(0)

            st.text_area(
                "Resume Content",
                text_content,
                height=600,
                disabled=True,
                label_visibility="collapsed"
            )

        elif file_extension == 'docx':
            st.info("📝 DOCX Preview - Showing text content")

            try:
                import docx
                import io

                doc = docx.Document(io.BytesIO(uploaded_resume.read()))
                uploaded_resume.seek(0)

                text_content = ""
                for paragraph in doc.paragraphs:
                    text_content += paragraph.text + "\n"

                st.text_area(
                    "Resume Content",
                    text_content,
                    height=600,
                    disabled=True,
                    label_visibility="collapsed"
                )
            except Exception as e:
                st.error(f"Error reading DOCX: {e}")
                st.info("💡 Install python-docx: `pip install python-docx`")

        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("✖️ Close", width="stretch", type="primary"):
                st.session_state['show_modal'] = False
                st.rerun()

# Main content area
if search_button:
    if not search_term:
        st.error("❌ Please enter a job title!")
    else:
        # Process filters
        work_type_param = None if work_type == "Any" else work_type.replace("/", "-").lower()

        remote_param = None if remote_option == "Any" else remote_option.lower()

        salary_param = None
        if salary_filter != "Any":
            salary_param = int(salary_filter.replace("K+", "000"))

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
        active_filters = []
        if work_type != "Any":
            active_filters.append(f"📋 {work_type}")
        if remote_option != "Any":
            active_filters.append(f"🏠 {remote_option}")
        if salary_filter != "Any":
            active_filters.append(f"💰 {salary_filter}")
        if date_posted != "Any time":
            active_filters.append(f"📅 {date_posted}")

        if active_filters:
            st.info("**Active Filters:** " + " • ".join(active_filters))

        # Show loading spinner
        with st.spinner(f"🔎 Scraping SEEK for '{search_term}' jobs in {location}..."):
            try:
                # Run the scraper with filters
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
                csv_path = 'data/jobs.csv'
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)

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

                    # Display each job as a card
                    st.subheader("📋 Job Listings")

                    for idx, row in df.iterrows():
                        # Score job if resume is uploaded
                        match_score = None
                        if uploaded_resume and st.session_state.get('resume_profile'):
                            from LLM_Scorer import score_job_match

                            cache_key = f"score_{idx}"
                            if cache_key not in st.session_state:
                                with st.spinner(f"🤖 Analyzing match for {row['title']}..."):
                                    match_score = score_job_match(row.to_dict(), st.session_state['resume_profile'])
                                    st.session_state[cache_key] = match_score
                            else:
                                match_score = st.session_state[cache_key]

                        with st.container():
                            col_main, col_side = st.columns([3, 1])

                            with col_main:
                                # Job title with match score
                                if match_score:
                                    score = match_score['score']
                                    if score >= 80:
                                        color = "🟢"
                                    elif score >= 60:
                                        color = "🟡"
                                    else:
                                        color = "🔴"

                                    st.markdown(f"### {color} [{row['title']}]({row['url']}) - **{score}% Match**")

                                    rec = match_score['recommendation']
                                    if rec == "Strong Match":
                                        st.success(f"✨ {rec}")
                                    elif rec == "Good Match":
                                        st.info(f"👍 {rec}")
                                    else:
                                        st.warning(f"🤔 {rec}")
                                else:
                                    st.markdown(f"### [{row['title']}]({row['url']})")

                                st.markdown(f"**🏢 {row['company']}** • 📍 {row['location']}")

                                if row['salary'] != 'Not specified':
                                    st.markdown(f"💰 **{row['salary']}**")
                                else:
                                    st.markdown(f"💰 {row['salary']}")

                                # AI Match Analysis
                                if match_score:
                                    with st.expander("🤖 AI Match Analysis", expanded=False):
                                        st.markdown(f"**Reasoning:** {match_score['reasoning']}")

                                        st.markdown("---")

                                        col_pros, col_cons = st.columns(2)
                                        with col_pros:
                                            st.markdown("**✅ Pros:**")
                                            for pro in match_score['pros']:
                                                st.markdown(f"- {pro}")
                                        with col_cons:
                                            st.markdown("**⚠️ Cons:**")
                                            for con in match_score['cons']:
                                                st.markdown(f"- {con}")

                                        st.markdown("---")

                                        # Strong Matches
                                        if match_score.get('strong_matches'):
                                            st.markdown(
                                                f"**🎯 Strong Matches:** ({match_score['skill_match_percentage']}% skill match)")
                                            for match in match_score['strong_matches']:
                                                st.markdown(f"✅ {match}")

                                        # Gaps
                                        if match_score.get('gaps'):
                                            st.markdown("**⚠️ Gaps:**")
                                            for gap in match_score['gaps']:
                                                st.markdown(f"⚠️ {gap}")

                                        st.markdown("---")

                                        # Strategic Considerations
                                        if match_score.get('strategic_considerations'):
                                            st.markdown("**💡 Strategic Considerations:**")
                                            for idx_strat, consideration in enumerate(
                                                    match_score['strategic_considerations'], 1):
                                                st.markdown(f"{idx_strat}. {consideration}")

                                # Description
                                if row['full_description'] != 'N/A' and row[
                                    'full_description'] != 'Description not available':
                                    with st.expander("📄 View Full Description"):
                                        st.write(row['full_description'])
                                elif row['short_description'] != 'N/A':
                                    with st.expander("📄 View Short Description"):
                                        st.write(row['short_description'])

                            with col_side:
                                st.link_button("Apply Now", row['url'], width="stretch")

                            st.markdown("---")

                    # Download button
                    st.download_button(
                        label="📥 Download as CSV",
                        data=df.to_csv(index=False).encode('utf-8'),
                        file_name=f"{search_term.replace(' ', '_')}_jobs.csv",
                        mime="text/csv",
                        width="stretch"
                    )

                else:
                    st.error("❌ No jobs file found. Please try searching again.")

            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                st.exception(e)

else:
    # Welcome screen
    st.info("👈 Enter your search criteria in the sidebar and click 'Search Jobs' to get started!")

    csv_path = 'data/jobs.csv'
    if os.path.exists(csv_path):
        st.subheader("📊 Previous Search Results")
        df = pd.read_csv(csv_path)
        st.dataframe(df, width="stretch", hide_index=True)