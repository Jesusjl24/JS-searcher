"""
Anti-blocking strategies for web scraping
Implements multiple FREE techniques to avoid IP blocks and rate limiting
"""

import random
import time
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# USER AGENT ROTATION
# ============================================================================

# Real browser user agents (frequently updated)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",

    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",

    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",

    # Firefox on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",

    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",

    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    """
    Get a random user agent string

    Returns:
        Random user agent string
    """
    agent = random.choice(USER_AGENTS)
    logger.debug(f"Selected user agent: {agent[:50]}...")
    return agent


# ============================================================================
# REQUEST HEADERS RANDOMIZATION
# ============================================================================

def get_random_headers(include_user_agent: bool = True) -> Dict[str, str]:
    """
    Generate randomized request headers to mimic real browsers

    Args:
        include_user_agent: Whether to include User-Agent header

    Returns:
        Dictionary of HTTP headers
    """
    headers = {}

    if include_user_agent:
        headers["User-Agent"] = get_random_user_agent()

    # Accept headers (browsers send these)
    headers["Accept"] = random.choice([
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ])

    # Accept-Language (randomize to appear from different locations)
    headers["Accept-Language"] = random.choice([
        "en-US,en;q=0.9",
        "en-AU,en;q=0.9",
        "en-GB,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
    ])

    # Accept-Encoding
    headers["Accept-Encoding"] = "gzip, deflate, br"

    # Connection
    headers["Connection"] = "keep-alive"

    # Upgrade-Insecure-Requests
    headers["Upgrade-Insecure-Requests"] = "1"

    # DNT (Do Not Track) - sometimes helps
    if random.random() > 0.5:
        headers["DNT"] = "1"

    # Sec-Fetch headers (modern browsers send these)
    headers["Sec-Fetch-Dest"] = "document"
    headers["Sec-Fetch-Mode"] = "navigate"
    headers["Sec-Fetch-Site"] = random.choice(["none", "same-origin", "cross-site"])
    headers["Sec-Fetch-User"] = "?1"

    logger.debug(f"Generated {len(headers)} random headers")
    return headers


# ============================================================================
# INTELLIGENT RATE LIMITING
# ============================================================================

class IntelligentRateLimiter:
    """
    Smart rate limiter with multiple strategies to avoid detection
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 5.0,
        jitter: bool = True,
        human_like: bool = True
    ):
        """
        Initialize rate limiter

        Args:
            base_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
            jitter: Add random variation to delays
            human_like: Use human-like delay patterns
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.human_like = human_like
        self.last_request_time = None
        self.request_count = 0

    def wait(self):
        """
        Wait appropriate amount of time before next request
        Uses human-like patterns and jitter
        """
        if self.last_request_time is None:
            self.last_request_time = time.time()
            return

        # Calculate base delay
        delay = random.uniform(self.base_delay, self.max_delay)

        # Add jitter (random variation)
        if self.jitter:
            jitter_amount = delay * random.uniform(-0.3, 0.3)
            delay += jitter_amount

        # Human-like patterns: occasionally pause longer
        if self.human_like:
            self.request_count += 1

            # Every 5-10 requests, take a longer break (simulates reading)
            if self.request_count % random.randint(5, 10) == 0:
                extra_delay = random.uniform(5, 15)
                delay += extra_delay
                logger.info(f"Taking human-like break: {extra_delay:.1f}s extra")

            # Very occasionally take a very long break (simulates stepping away)
            if random.random() < 0.05:  # 5% chance
                long_break = random.uniform(30, 60)
                delay += long_break
                logger.info(f"Taking extended break: {long_break:.1f}s")

        # Ensure we don't exceed max delay (unless human-like pattern added more)
        if not self.human_like or delay < self.max_delay * 3:
            delay = min(delay, self.max_delay * 2)

        logger.debug(f"Waiting {delay:.2f}s before next request")
        time.sleep(delay)

        self.last_request_time = time.time()

    def reset(self):
        """Reset the rate limiter"""
        self.last_request_time = None
        self.request_count = 0


# ============================================================================
# TIME-BASED REQUEST SCHEDULING
# ============================================================================

class TimeBasedScheduler:
    """
    Schedule requests during optimal times to avoid detection
    """

    def __init__(
        self,
        respect_business_hours: bool = True,
        avoid_peaks: bool = True
    ):
        """
        Initialize scheduler

        Args:
            respect_business_hours: Only scrape during business hours
            avoid_peaks: Avoid peak traffic times
        """
        self.respect_business_hours = respect_business_hours
        self.avoid_peaks = avoid_peaks

    def should_scrape_now(self) -> bool:
        """
        Check if current time is good for scraping

        Returns:
            True if it's a good time to scrape
        """
        now = datetime.now()
        hour = now.hour

        # Business hours: 9 AM - 6 PM (more natural)
        if self.respect_business_hours:
            if hour < 9 or hour > 18:
                logger.warning(f"Outside business hours ({hour}:00). Consider waiting.")
                return False

        # Avoid peak times: 12-1 PM (lunch), 5-6 PM (end of day)
        if self.avoid_peaks:
            if (12 <= hour < 13) or (17 <= hour < 18):
                logger.info(f"Peak time ({hour}:00). Recommend waiting to reduce load.")
                return False

        return True

    def get_recommended_delay(self) -> float:
        """
        Get recommended delay based on current time

        Returns:
            Recommended delay in seconds
        """
        now = datetime.now()
        hour = now.hour

        # Night time: can be more aggressive (less competition)
        if 22 <= hour or hour < 6:
            return random.uniform(1.0, 2.0)

        # Business hours: be more conservative
        elif 9 <= hour < 18:
            return random.uniform(3.0, 6.0)

        # Other times: moderate
        else:
            return random.uniform(2.0, 4.0)


# ============================================================================
# BROWSER FINGERPRINT RANDOMIZATION
# ============================================================================

def get_random_viewport() -> tuple:
    """
    Get random viewport size (common screen resolutions)

    Returns:
        Tuple of (width, height)
    """
    viewports = [
        (1920, 1080),  # Full HD
        (1366, 768),   # Common laptop
        (1536, 864),   # Common laptop
        (1440, 900),   # MacBook
        (2560, 1440),  # QHD
        (1280, 720),   # HD
    ]
    return random.choice(viewports)


def get_random_timezone() -> str:
    """
    Get random timezone (Australian timezones for SEEK)

    Returns:
        Timezone string
    """
    timezones = [
        "Australia/Sydney",
        "Australia/Melbourne",
        "Australia/Brisbane",
        "Australia/Perth",
        "Australia/Adelaide",
    ]
    return random.choice(timezones)


# ============================================================================
# PROXY MANAGER (Infrastructure for future use)
# ============================================================================

class ProxyManager:
    """
    Proxy rotation manager

    Note: Free proxies are often unreliable. Better to use other anti-blocking
    techniques. This class provides infrastructure if you get access to
    paid proxy services.
    """

    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize proxy manager

        Args:
            proxies: List of proxy URLs (format: "http://ip:port")
        """
        self.proxies = proxies or []
        self.current_index = 0
        self.failed_proxies = set()

        logger.info(f"Initialized with {len(self.proxies)} proxies")

    def get_next_proxy(self) -> Optional[str]:
        """
        Get next working proxy

        Returns:
            Proxy URL or None if no proxies available
        """
        if not self.proxies:
            return None

        # Try to find a non-failed proxy
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)

            if proxy not in self.failed_proxies:
                logger.debug(f"Using proxy: {proxy}")
                return proxy

            attempts += 1

        logger.warning("All proxies have failed")
        return None

    def mark_proxy_failed(self, proxy: str):
        """
        Mark a proxy as failed

        Args:
            proxy: Proxy URL that failed
        """
        self.failed_proxies.add(proxy)
        logger.warning(f"Marked proxy as failed: {proxy}")

    def reset_failed_proxies(self):
        """Reset the failed proxies set (give them another chance)"""
        self.failed_proxies.clear()
        logger.info("Reset failed proxies")


# ============================================================================
# SESSION ROTATION
# ============================================================================

class SessionRotator:
    """
    Manage multiple scraping sessions to distribute load
    """

    def __init__(self, session_lifetime: int = 10):
        """
        Initialize session rotator

        Args:
            session_lifetime: Number of requests before rotating session
        """
        self.session_lifetime = session_lifetime
        self.current_session_requests = 0
        self.session_start_time = time.time()

    def should_rotate(self) -> bool:
        """
        Check if session should be rotated

        Returns:
            True if session should be rotated
        """
        self.current_session_requests += 1

        # Rotate after certain number of requests
        if self.current_session_requests >= self.session_lifetime:
            logger.info(f"Rotating session after {self.current_session_requests} requests")
            return True

        # Also rotate after certain time (30 minutes)
        if time.time() - self.session_start_time > 1800:
            logger.info("Rotating session after 30 minutes")
            return True

        return False

    def reset_session(self):
        """Reset session counters"""
        self.current_session_requests = 0
        self.session_start_time = time.time()
        logger.info("Session reset")


# ============================================================================
# EXPONENTIAL BACKOFF
# ============================================================================

class ExponentialBackoff:
    """
    Implement exponential backoff for retries
    """

    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize exponential backoff

        Args:
            base_delay: Initial delay
            max_delay: Maximum delay
            exponential_base: Base for exponential growth
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.attempt = 0

    def wait(self):
        """Wait with exponential backoff"""
        delay = min(
            self.base_delay * (self.exponential_base ** self.attempt),
            self.max_delay
        )

        # Add jitter
        delay = delay * random.uniform(0.8, 1.2)

        logger.info(f"Backoff attempt {self.attempt + 1}: waiting {delay:.2f}s")
        time.sleep(delay)

        self.attempt += 1

    def reset(self):
        """Reset backoff counter"""
        self.attempt = 0


# ============================================================================
# COMBINED ANTI-BLOCKING STRATEGY
# ============================================================================

class AntiBlockingStrategy:
    """
    Combined anti-blocking strategy using multiple techniques
    """

    def __init__(
        self,
        use_rate_limiting: bool = True,
        use_header_rotation: bool = True,
        use_session_rotation: bool = True,
        use_time_scheduling: bool = False,  # Optional
        proxies: Optional[List[str]] = None
    ):
        """
        Initialize combined anti-blocking strategy

        Args:
            use_rate_limiting: Enable intelligent rate limiting
            use_header_rotation: Enable header rotation
            use_session_rotation: Enable session rotation
            use_time_scheduling: Enable time-based scheduling
            proxies: Optional list of proxy URLs
        """
        self.rate_limiter = IntelligentRateLimiter() if use_rate_limiting else None
        self.use_header_rotation = use_header_rotation
        self.session_rotator = SessionRotator() if use_session_rotation else None
        self.time_scheduler = TimeBasedScheduler() if use_time_scheduling else None
        self.proxy_manager = ProxyManager(proxies) if proxies else None

        logger.info("Anti-blocking strategy initialized")

    def before_request(self) -> Dict:
        """
        Execute before making a request

        Returns:
            Dictionary with request parameters (headers, proxy, etc.)
        """
        params = {}

        # Check if it's a good time to scrape
        if self.time_scheduler and not self.time_scheduler.should_scrape_now():
            logger.warning("Not optimal time for scraping")

        # Wait according to rate limiter
        if self.rate_limiter:
            self.rate_limiter.wait()

        # Get random headers
        if self.use_header_rotation:
            params['headers'] = get_random_headers()

        # Get proxy if available
        if self.proxy_manager:
            proxy = self.proxy_manager.get_next_proxy()
            if proxy:
                params['proxy'] = proxy

        return params

    def after_request(self, success: bool = True):
        """
        Execute after request completes

        Args:
            success: Whether request was successful
        """
        # Check if session should rotate
        if self.session_rotator and self.session_rotator.should_rotate():
            return True  # Signal that driver should be recreated

        return False

    def handle_failure(self, proxy: Optional[str] = None):
        """
        Handle request failure

        Args:
            proxy: Proxy that was used (if any)
        """
        if proxy and self.proxy_manager:
            self.proxy_manager.mark_proxy_failed(proxy)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_anti_blocking_chrome_options(headless: bool = True):
    """
    Get Chrome options configured for anti-blocking

    Args:
        headless: Run in headless mode

    Returns:
        Configured ChromeOptions object
    """
    from selenium.webdriver.chrome.options import Options

    options = Options()

    # Basic settings
    if headless:
        options.add_argument("--headless")

    # Anti-detection arguments
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Random user agent
    options.add_argument(f"user-agent={get_random_user_agent()}")

    # Random viewport
    width, height = get_random_viewport()
    options.add_argument(f"--window-size={width},{height}")

    # Additional stealth options
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")

    # Disable images for faster loading (optional)
    # prefs = {"profile.managed_default_content_settings.images": 2}
    # options.add_experimental_option("prefs", prefs)

    logger.info(f"Configured anti-blocking Chrome options (viewport: {width}x{height})")

    return options
