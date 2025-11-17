# JS-searcher

🔍 **AI-Powered Job Search Application for SEEK**

An intelligent job search tool that scrapes SEEK.com.au and uses AI to match jobs with your resume, providing personalized recommendations.

---

## ✨ Features

- **Smart Job Scraping**: Automatically scrapes job listings from SEEK with advanced filtering
- **AI-Powered Matching**: Uses Mistral AI to analyze your resume and score job matches
- **Advanced Filters**: Filter by work type, location, salary, and posting date
- **Resume Analysis**: Extracts skills, experience, and qualifications from your resume (PDF, DOCX, TXT)
- **Match Insights**: Get detailed pros, cons, and strategic considerations for each job
- **Beautiful UI**: Clean Streamlit interface with job cards, metrics, and visualizations
- **Export Results**: Download job listings as CSV for further analysis

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium)
- Mistral API key ([Get one here](https://mistral.ai))

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd JS-searcher
```

2. **Create virtual environment** (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

Create a `.env` file in the root directory:
```env
MISTRAL_API_KEY=your_mistral_api_key_here
```

5. **Run the application**
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📋 Usage

### Basic Job Search

1. Enter job title (e.g., "Project Manager")
2. Enter location (e.g., "Sydney")
3. Click "Search Jobs"

### Advanced Search with Filters

Use the sidebar filters to refine your search:
- **Work Type**: Full time, Part time, Contract, Casual
- **Work Location**: On-site, Hybrid, Remote
- **Minimum Salary**: Select from predefined ranges
- **Date Posted**: Filter by recency

### AI-Powered Resume Matching

1. Upload your resume (PDF, DOCX, or TXT)
2. The AI will automatically analyze your:
   - Skills (technical and soft)
   - Years of experience
   - Education and certifications
   - Previous roles and industries
3. Search for jobs as normal
4. Each job will show:
   - Match score (0-100%)
   - Match recommendation (Strong/Good/Moderate/Weak)
   - Detailed analysis with pros, cons, and strategic advice

---

## 🏗️ Project Structure

```
JS-searcher/
├── .env                    # API keys (create this)
├── .gitignore             # Git ignore file
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── app.py                # Main Streamlit application
├── config.py             # Configuration constants
│
├── src/                  # Source code
│   ├── __init__.py
│   ├── scraper.py        # SEEK job scraper
│   ├── llm_scorer.py     # AI resume parser and job matcher
│   ├── file_handlers.py  # Resume file processing
│   └── utils.py          # Utility functions
│
├── tests/                # Unit tests
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_llm_scorer.py
│   ├── test_file_handlers.py
│   └── test_utils.py
│
└── data/                 # Data directory (auto-created)
    └── jobs.csv          # Scraped jobs (auto-generated)
```

---

## 🔧 Configuration

Edit `config.py` to customize:

### Scraping Settings
```python
SCRAPING_CONFIG = {
    "max_jobs_limit": 50,          # Maximum jobs per search
    "request_delay_min": 2,        # Minimum delay between requests
    "request_delay_max": 4,        # Maximum delay between requests
    "max_retries": 3,              # Retry attempts for failed requests
}
```

### LLM Settings
```python
LLM_CONFIG = {
    "model": "mistral-small-latest",
    "resume_max_chars": 5000,
    "job_description_max_chars": 2000,
    "temperature": 0.3,
}
```

### Resume Upload Settings
```python
RESUME_CONFIG = {
    "max_file_size_mb": 10,
    "allowed_extensions": ["pdf", "docx", "txt"],
}
```

---

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_utils.py

# Run with coverage
pytest --cov=src tests/
```

### Manual Testing

Test individual modules:

```bash
# Test scraper
python src/scraper.py

# Test LLM scorer
python src/llm_scorer.py
```

---

## 📊 How It Works

### 1. Job Scraping

The scraper uses Selenium to:
1. Build a SEEK URL with your search criteria
2. Navigate to the search results page
3. Extract job cards using BeautifulSoup
4. Parse job details (title, company, location, salary, description)
5. Optionally fetch full descriptions from individual job pages
6. Save results to CSV

### 2. Resume Analysis

The AI resume parser:
1. Extracts text from your resume (supports PDF, DOCX, TXT)
2. Sends text to Mistral AI with structured prompting
3. Parses response to extract:
   - Technical and soft skills
   - Years of experience
   - Education and certifications
   - Previous job titles
   - Industries worked in
   - Career achievements

### 3. Job Matching

The AI job matcher:
1. Takes your resume profile and job details
2. Sends both to Mistral AI for comparison
3. Returns comprehensive analysis:
   - Overall match score (0-100)
   - Skill match percentage
   - Detailed reasoning
   - Pros and cons
   - Identified gaps
   - Strategic considerations

---

## ⚙️ Architecture

### Key Design Patterns

- **Modular Architecture**: Separation of concerns with dedicated modules
- **Context Managers**: Proper resource cleanup for Selenium drivers
- **Error Handling**: Custom exceptions and graceful degradation
- **Retry Logic**: Automatic retries with exponential backoff
- **Smart Truncation**: Sentence-boundary-aware text truncation
- **Input Validation**: Sanitization and validation of all user inputs

### Performance Optimizations

- **Caching**: Session state caching for job scores
- **Rate Limiting**: Configurable delays between requests
- **Lazy Loading**: Full descriptions fetched only when needed
- **Resource Pooling**: Context managers for driver lifecycle

---

## 🛡️ Security Considerations

### Implemented Protections

✅ **Input Sanitization**: All search terms and locations are sanitized
✅ **File Validation**: Resume uploads validated for type and size
✅ **API Key Protection**: Environment variables for sensitive data
✅ **Rate Limiting**: Prevents overwhelming SEEK servers
✅ **Error Handling**: Graceful failures without exposing internals

### Best Practices

- Never commit `.env` file (in `.gitignore`)
- Validate all user inputs before processing
- Use HTTPS for all API calls
- Limit file upload sizes
- Implement request rate limiting

---

## ⚠️ Limitations & Considerations

### Rate Limiting
- Default: 5 jobs per search
- Recommendation: Keep searches small to avoid IP bans
- SEEK may block excessive requests

### AI Accuracy
- AI analysis is probabilistic, not guaranteed
- Review all job matches manually
- Results depend on resume quality and job description detail

### Browser Requirements
- Requires Chrome browser installed
- Headless mode enabled by default
- May require ChromeDriver updates

---

## 🐛 Troubleshooting

### Common Issues

**"ChromeDriver not found"**
```bash
# The app auto-downloads ChromeDriver, but if it fails:
pip install --upgrade webdriver-manager
```

**"MISTRAL_API_KEY not found"**
```bash
# Create .env file with:
echo "MISTRAL_API_KEY=your_key_here" > .env
```

**"Module not found" errors**
```bash
# Reinstall dependencies:
pip install -r requirements.txt --force-reinstall
```

**Resume parsing fails**
```bash
# Check file format:
# - PDF: Must be text-based (not scanned images)
# - DOCX: Must be valid Word document
# - TXT: Must be UTF-8 encoded
```

**No jobs found**
```bash
# Try:
# 1. Broader search terms
# 2. Fewer filters
# 3. Different location
# 4. Wait a few minutes (possible rate limiting)
```

---

## 📈 Future Enhancements

### Planned Features
- [ ] Multi-page job scraping
- [ ] Job alert notifications
- [ ] Application tracking
- [ ] Resume optimization suggestions
- [ ] Cover letter generation
- [ ] Batch job scoring
- [ ] Database storage
- [ ] User authentication
- [ ] Mobile app

### Contributions Welcome!

See `CONTRIBUTING.md` for guidelines.

---

## 📝 License

This project is for educational purposes. Please respect SEEK's terms of service and rate limits.

**Note**: Web scraping should be done responsibly:
- Use reasonable rate limits
- Don't overwhelm servers
- Respect robots.txt
- Check terms of service

---

## 🙏 Acknowledgments

- **SEEK**: For providing job listings
- **Mistral AI**: For LLM capabilities
- **Streamlit**: For the amazing UI framework
- **Selenium**: For web scraping capabilities

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting section

---

## 🔄 Version History

### Version 2.0.0 (Current)
- ✅ Complete refactoring with modular architecture
- ✅ Improved error handling and logging
- ✅ Added comprehensive unit tests
- ✅ Enhanced AI prompts and parsing
- ✅ Better resource management
- ✅ Configuration-driven design
- ✅ Security improvements

### Version 1.0.0
- Basic SEEK scraping
- Simple resume matching
- Streamlit UI

---

**Happy Job Hunting! 🎯**
