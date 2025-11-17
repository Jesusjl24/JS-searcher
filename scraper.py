import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def scrape_seek_jobs_selenium(search_term, location="Sydney", max_jobs=10,
                              work_type=None, remote_option=None,
                              salary_min=None, date_posted=None):
    """
    Scrape job listings from SEEK using Selenium with advanced filters

    Args:
        search_term: Job title to search for
        location: Location to search in
        max_jobs: Maximum number of jobs to scrape
        work_type: "full-time", "part-time", "contract", "casual" or None
        remote_option: "on-site", "hybrid", "remote" or None
        salary_min: Minimum salary (e.g., 80000) or None
        date_posted: "today", "3", "7", "14", "30" (days) or None
    """
    formatted_search = search_term.lower().replace(" ", "-")
    base_url = "https://www.seek.com.au"
    search_url = f"{base_url}/{formatted_search}-jobs/in-{location}"

    # Build query parameters for filters
    params = []

    # Work type filter
    if work_type:
        work_type_map = {
            "full-time": "fullTime=true",
            "part-time": "partTime=true",
            "contract": "contract=true",
            "casual": "casual=true"
        }
        if work_type.lower() in work_type_map:
            params.append(work_type_map[work_type.lower()])

    # Remote option filter
    if remote_option:
        remote_map = {
            "remote": "worktype=work-from-home",
            "hybrid": "worktype=hybrid",
            "on-site": "worktype=office"
        }
        if remote_option.lower() in remote_map:
            params.append(remote_map[remote_option.lower()])

    # Salary filter
    if salary_min:
        params.append(f"salarytype=annual&salaryrange={salary_min}-")

    # Date posted filter
    if date_posted:
        if date_posted == "today":
            params.append("daterange=1")
        else:
            params.append(f"daterange={date_posted}")

    # Add parameters to URL
    if params:
        search_url += "?" + "&".join(params)

    print(f"Scraping: {search_url}")

    # ... rest of your existing scraper code stays the same ...

def get_full_job_description(job_url):
    """
    Visit individual job page and extract full description

    Args:
        job_url: URL of the specific job posting

    Returns:
        String with full job description
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        print(f"  📄 Fetching full description from: {job_url[:50]}...")
        driver.get(job_url)
        time.sleep(3)  # Be respectful

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        # SEEK job descriptions are usually in a div with specific attributes
        # We'll try multiple selectors to find it
        description = ""

        # Try different selectors
        desc_element = soup.find('div', attrs={'data-automation': 'jobAdDetails'})
        if not desc_element:
            desc_element = soup.find('div', class_=lambda x: x and 'job-description' in x.lower())
        if not desc_element:
            # Fallback: find the largest text block
            all_divs = soup.find_all('div')
            desc_element = max(all_divs, key=lambda x: len(x.get_text()), default=None)

        if desc_element:
            description = desc_element.get_text(separator='\n', strip=True)
            print(f"  ✅ Got {len(description)} characters")
        else:
            print(f"  ⚠️ Couldn't find full description")
            description = "Description not available"

        return description

    except Exception as e:
        print(f"  ❌ Error fetching description: {e}")
        return "Error fetching description"

    finally:
        driver.quit()


if __name__ == "__main__":
    print("🎓 Testing SEEK Scraper with Selenium...")
    scrape_seek_jobs_selenium("Project manager", "Sydney", max_jobs=5)