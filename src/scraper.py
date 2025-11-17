"""
Web scraper for SEEK job listings
Uses Selenium for dynamic content loading with proper resource management
"""

import logging
import time
import pandas as pd
from typing import Optional, List, Dict
from contextlib import contextmanager
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from config import SCRAPING_CONFIG, SELENIUM_CONFIG, JOBS_CSV_PATH, ANTI_BLOCKING_CONFIG
from src.utils import build_seek_url, random_delay, validate_max_jobs, clean_text
from src.anti_blocking import (
    AntiBlockingStrategy,
    get_anti_blocking_chrome_options,
    get_random_user_agent,
)

# Configure logging
logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors"""
    pass


class DriverInitializationError(ScraperError):
    """Raised when WebDriver cannot be initialized"""
    pass


class ScrapingError(ScraperError):
    """Raised when scraping fails"""
    pass


@contextmanager
def get_chrome_driver(use_anti_blocking: bool = True):
    """
    Context manager for Chrome WebDriver with anti-blocking support
    Ensures proper cleanup even if errors occur

    Args:
        use_anti_blocking: Whether to use anti-blocking features

    Yields:
        WebDriver instance

    Raises:
        DriverInitializationError: If driver cannot be initialized
    """
    driver = None
    try:
        # Use anti-blocking options if enabled
        if use_anti_blocking and ANTI_BLOCKING_CONFIG["enabled"]:
            logger.info("Using anti-blocking Chrome options")
            chrome_options = get_anti_blocking_chrome_options(
                headless=SELENIUM_CONFIG["headless"]
            )
        else:
            # Fallback to standard config
            chrome_options = Options()

            # Configure options from config
            if SELENIUM_CONFIG["headless"]:
                chrome_options.add_argument("--headless")

            if SELENIUM_CONFIG["no_sandbox"]:
                chrome_options.add_argument("--no-sandbox")

            if SELENIUM_CONFIG["disable_gpu"]:
                chrome_options.add_argument("--disable-gpu")

            if SELENIUM_CONFIG["disable_dev_shm"]:
                chrome_options.add_argument("--disable-dev-shm-usage")

            # Anti-detection measures
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # User agent
            chrome_options.add_argument(f"user-agent={SELENIUM_CONFIG['user_agent']}")

            # Window size
            chrome_options.add_argument(f"--window-size={SELENIUM_CONFIG['window_size']}")

        # Initialize driver
        logger.info("Initializing Chrome WebDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set timeouts
        driver.set_page_load_timeout(SCRAPING_CONFIG["page_load_timeout"])

        logger.info("WebDriver initialized successfully")
        yield driver

    except Exception as e:
        logger.error(f"Failed to initialize WebDriver: {e}")
        raise DriverInitializationError(f"Could not initialize Chrome driver: {str(e)}")

    finally:
        if driver:
            try:
                driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")


class JobScraper:
    """
    Job scraper class for SEEK website
    Handles job listing extraction and description fetching
    """

    def __init__(self, driver):
        """
        Initialize scraper with WebDriver

        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, SCRAPING_CONFIG["element_wait_timeout"])

    def fetch_page(self, url: str, retries: int = None) -> bool:
        """
        Fetch a page with retry logic

        Args:
            url: URL to fetch
            retries: Number of retries (uses config default if None)

        Returns:
            True if successful, False otherwise
        """
        max_retries = retries or SCRAPING_CONFIG["max_retries"]

        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching URL (attempt {attempt + 1}/{max_retries}): {url}")
                self.driver.get(url)

                # Wait for page to load
                time.sleep(2)

                return True

            except TimeoutException:
                logger.warning(f"Timeout loading page (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(SCRAPING_CONFIG["retry_delay"])
                    continue
                else:
                    logger.error(f"Failed to load page after {max_retries} attempts")
                    return False

            except WebDriverException as e:
                logger.error(f"WebDriver error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(SCRAPING_CONFIG["retry_delay"])
                    continue
                else:
                    return False

        return False

    def extract_job_cards(self) -> List[BeautifulSoup]:
        """
        Extract job card elements from current page

        Returns:
            List of BeautifulSoup job card elements
        """
        try:
            # Get page source and parse with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Find job cards - SEEK uses article tags with specific data attributes
            job_cards = soup.find_all('article', attrs={'data-card-type': 'JobCard'})

            if not job_cards:
                # Fallback: try alternative selectors
                job_cards = soup.find_all('article')
                job_cards = [card for card in job_cards if 'job' in str(card).lower()]

            logger.info(f"Found {len(job_cards)} job cards on page")
            return job_cards

        except Exception as e:
            logger.error(f"Error extracting job cards: {e}")
            return []

    def parse_job_card(self, card: BeautifulSoup) -> Optional[Dict]:
        """
        Parse individual job card to extract job details

        Args:
            card: BeautifulSoup job card element

        Returns:
            Dictionary with job details or None if parsing fails
        """
        try:
            job_data = {}

            # Extract job title and URL
            title_elem = card.find('a', attrs={'data-automation': 'jobTitle'})
            if title_elem:
                job_data['title'] = clean_text(title_elem.get_text())
                job_data['url'] = SCRAPING_CONFIG["base_url"] + title_elem.get('href', '')
            else:
                # Try alternative selector
                title_elem = card.find('h3') or card.find('h2')
                if title_elem:
                    job_data['title'] = clean_text(title_elem.get_text())
                    link = card.find('a')
                    job_data['url'] = SCRAPING_CONFIG["base_url"] + link.get('href', '') if link else ''
                else:
                    logger.warning("Could not find job title")
                    return None

            # Extract company name
            company_elem = card.find('a', attrs={'data-automation': 'jobCompany'})
            if not company_elem:
                company_elem = card.find('span', attrs={'data-automation': 'jobCompany'})
            job_data['company'] = clean_text(company_elem.get_text()) if company_elem else 'N/A'

            # Extract location
            location_elem = card.find('a', attrs={'data-automation': 'jobLocation'})
            if not location_elem:
                location_elem = card.find('span', attrs={'data-automation': 'jobLocation'})
            job_data['location'] = clean_text(location_elem.get_text()) if location_elem else 'N/A'

            # Extract salary
            salary_elem = card.find('span', attrs={'data-automation': 'jobSalary'})
            job_data['salary'] = clean_text(salary_elem.get_text()) if salary_elem else 'Not specified'

            # Extract short description
            desc_elem = card.find('span', attrs={'data-automation': 'jobShortDescription'})
            job_data['short_description'] = clean_text(desc_elem.get_text()) if desc_elem else 'N/A'

            # Initialize full description as N/A (will be fetched separately)
            job_data['full_description'] = 'N/A'

            logger.debug(f"Parsed job: {job_data['title']} at {job_data['company']}")
            return job_data

        except Exception as e:
            logger.error(f"Error parsing job card: {e}")
            return None

    def fetch_full_description(self, job_url: str) -> str:
        """
        Fetch full job description from job detail page

        Args:
            job_url: URL of the job posting

        Returns:
            Full job description text
        """
        # Create a new driver instance for description fetching
        with get_chrome_driver() as desc_driver:
            try:
                logger.debug(f"Fetching full description from: {job_url[:50]}...")
                desc_driver.get(job_url)

                # Wait for description to load
                time.sleep(3)

                page_source = desc_driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')

                # Try multiple selectors for job description
                desc_element = soup.find('div', attrs={'data-automation': 'jobAdDetails'})

                if not desc_element:
                    desc_element = soup.find('div', class_=lambda x: x and 'job-description' in x.lower())

                if not desc_element:
                    # Fallback: find the largest text block
                    all_divs = soup.find_all('div')
                    desc_element = max(all_divs, key=lambda x: len(x.get_text()), default=None)

                if desc_element:
                    description = desc_element.get_text(separator='\n', strip=True)
                    logger.debug(f"Fetched {len(description)} characters")
                    return clean_text(description)
                else:
                    logger.warning("Could not find full description")
                    return "Description not available"

            except Exception as e:
                logger.error(f"Error fetching description: {e}")
                return "Error fetching description"


def scrape_seek_jobs(
    search_term: str,
    location: str = "Sydney",
    max_jobs: int = 5,
    work_type: Optional[str] = None,
    remote_option: Optional[str] = None,
    salary_min: Optional[int] = None,
    date_posted: Optional[str] = None,
    fetch_full_descriptions: bool = True
) -> pd.DataFrame:
    """
    Scrape job listings from SEEK

    Args:
        search_term: Job title to search for
        location: Location to search in
        max_jobs: Maximum number of jobs to scrape
        work_type: Employment type filter
        remote_option: Remote work filter
        salary_min: Minimum salary filter
        date_posted: Date posted filter
        fetch_full_descriptions: Whether to fetch full job descriptions

    Returns:
        DataFrame with job listings

    Raises:
        ScraperError: If scraping fails
    """
    # Validate inputs
    max_jobs = validate_max_jobs(max_jobs)

    # Build URL
    search_url = build_seek_url(
        search_term=search_term,
        location=location,
        work_type=work_type,
        remote_option=remote_option,
        salary_min=salary_min,
        date_posted=date_posted
    )

    jobs_data = []

    # Initialize anti-blocking strategy if enabled
    anti_blocking = None
    if ANTI_BLOCKING_CONFIG["enabled"]:
        logger.info("Initializing anti-blocking strategy")
        anti_blocking = AntiBlockingStrategy(
            use_rate_limiting=ANTI_BLOCKING_CONFIG["use_rate_limiting"],
            use_header_rotation=ANTI_BLOCKING_CONFIG["use_header_rotation"],
            use_session_rotation=ANTI_BLOCKING_CONFIG["use_session_rotation"],
            use_time_scheduling=ANTI_BLOCKING_CONFIG["use_time_scheduling"],
            proxies=ANTI_BLOCKING_CONFIG["proxies"] if ANTI_BLOCKING_CONFIG["proxies"] else None
        )

    try:
        with get_chrome_driver(use_anti_blocking=True) as driver:
            scraper = JobScraper(driver)

            # Fetch search results page
            if not scraper.fetch_page(search_url):
                raise ScrapingError("Failed to load search results page")

            # Extract job cards
            job_cards = scraper.extract_job_cards()

            if not job_cards:
                logger.warning("No job cards found on page")
                return pd.DataFrame()

            # Limit to max_jobs
            job_cards = job_cards[:max_jobs]

            # Parse each job card
            for idx, card in enumerate(job_cards, 1):
                logger.info(f"Processing job {idx}/{len(job_cards)}")

                job_data = scraper.parse_job_card(card)

                if job_data:
                    jobs_data.append(job_data)

                    # Use anti-blocking rate limiting if enabled, otherwise use standard delay
                    if idx < len(job_cards):
                        if anti_blocking:
                            anti_blocking.before_request()  # Smart delay with jitter
                        else:
                            random_delay()  # Fallback to standard delay

            logger.info(f"Successfully parsed {len(jobs_data)} jobs")

    except DriverInitializationError as e:
        logger.error(f"Driver initialization failed: {e}")
        raise ScraperError(f"Could not initialize browser: {str(e)}")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise ScraperError(f"An error occurred during scraping: {str(e)}")

    # Fetch full descriptions if requested
    if fetch_full_descriptions and jobs_data:
        logger.info("Fetching full descriptions...")

        for idx, job in enumerate(jobs_data, 1):
            try:
                logger.info(f"Fetching description {idx}/{len(jobs_data)}")

                with get_chrome_driver(use_anti_blocking=True) as driver:
                    scraper = JobScraper(driver)
                    full_desc = scraper.fetch_full_description(job['url'])
                    job['full_description'] = full_desc

                # Use anti-blocking rate limiting if enabled
                if idx < len(jobs_data):
                    if anti_blocking:
                        anti_blocking.before_request()  # Smart delay with jitter
                    else:
                        random_delay()  # Fallback to standard delay

            except Exception as e:
                logger.error(f"Error fetching description for {job['title']}: {e}")
                job['full_description'] = "Error fetching description"

    # Convert to DataFrame
    df = pd.DataFrame(jobs_data)

    # Save to CSV
    try:
        df.to_csv(JOBS_CSV_PATH, index=False)
        logger.info(f"Saved {len(df)} jobs to {JOBS_CSV_PATH}")
    except Exception as e:
        logger.error(f"Error saving to CSV: {e}")

    return df


# Legacy function for backward compatibility
def scrape_seek_jobs_selenium(
    search_term: str,
    location: str = "Sydney",
    max_jobs: int = 10,
    work_type: Optional[str] = None,
    remote_option: Optional[str] = None,
    salary_min: Optional[int] = None,
    date_posted: Optional[str] = None
) -> None:
    """
    Legacy function for backward compatibility with old app.py
    Scrapes jobs and saves to CSV

    Args:
        search_term: Job title to search for
        location: Location to search in
        max_jobs: Maximum number of jobs to scrape
        work_type: Employment type filter
        remote_option: Remote work filter
        salary_min: Minimum salary filter
        date_posted: Date posted filter
    """
    try:
        scrape_seek_jobs(
            search_term=search_term,
            location=location,
            max_jobs=max_jobs,
            work_type=work_type,
            remote_option=remote_option,
            salary_min=salary_min,
            date_posted=date_posted,
            fetch_full_descriptions=True
        )
    except ScraperError as e:
        logger.error(f"Scraping failed: {e}")
        raise


if __name__ == "__main__":
    # Setup logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🎓 Testing SEEK Scraper with Selenium...")
    try:
        df = scrape_seek_jobs("Project manager", "Sydney", max_jobs=3)
        print(f"\n✅ Successfully scraped {len(df)} jobs!")
        print("\nJob titles:")
        for idx, row in df.iterrows():
            print(f"  {idx + 1}. {row['title']} at {row['company']}")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
