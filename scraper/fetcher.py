"""Content fetcher supporting both static and dynamic pages."""

import asyncio
import time
from typing import Optional, Dict, Any
from enum import Enum

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


class FetchStrategy(Enum):
    """Fetching strategy."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    AUTO = "auto"


class ContentFetcher:
    """Fetches web content using multiple strategies."""

    def __init__(self, timeout: int = 30, user_agent: Optional[str] = None):
        """
        Initialize the fetcher.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string
        """
        self.timeout = timeout
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def fetch_static(self, url: str) -> Optional[str]:
        """
        Fetch content using static HTTP request.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if failed
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Static fetch failed for {url}: {e}")
            return None

    async def fetch_dynamic(self, url: str, wait_selector: Optional[str] = None) -> Optional[str]:
        """
        Fetch content using Playwright for JavaScript-rendered pages.

        Args:
            url: URL to fetch
            wait_selector: CSS selector to wait for before extracting content

        Returns:
            HTML content or None if failed
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

                # Wait for specific selector if provided
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=5000)
                    except PlaywrightTimeout:
                        pass

                # Additional wait for dynamic content
                await page.wait_for_timeout(2000)

                content = await page.content()
                await browser.close()

                return content

        except Exception as e:
            print(f"Dynamic fetch failed for {url}: {e}")
            return None

    async def fetch_with_scroll(self, url: str, scroll_count: int = 3) -> Optional[str]:
        """
        Fetch content with scrolling for infinite scroll pages.

        Args:
            url: URL to fetch
            scroll_count: Number of times to scroll

        Returns:
            HTML content or None if failed
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

                # Scroll multiple times
                for _ in range(scroll_count):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                content = await page.content()
                await browser.close()

                return content

        except Exception as e:
            print(f"Scroll fetch failed for {url}: {e}")
            return None

    def fetch(self, url: str, strategy: FetchStrategy = FetchStrategy.AUTO) -> Optional[str]:
        """
        Fetch content using the specified strategy.

        Args:
            url: URL to fetch
            strategy: Fetching strategy to use

        Returns:
            HTML content or None if failed
        """
        if strategy == FetchStrategy.STATIC:
            return self.fetch_static(url)

        elif strategy == FetchStrategy.DYNAMIC:
            return asyncio.run(self.fetch_dynamic(url))

        elif strategy == FetchStrategy.AUTO:
            # Try static first (faster)
            content = self.fetch_static(url)

            if content:
                # Check if page seems to have dynamic content
                soup = BeautifulSoup(content, 'lxml')

                # Indicators of dynamic content
                has_react = soup.find(id='root') or soup.find(id='app')
                has_spa_markers = bool(soup.find_all('script', src=lambda x: x and ('react' in x.lower() or 'vue' in x.lower() or 'angular' in x.lower())))
                has_minimal_content = len(soup.get_text(strip=True)) < 500

                # If likely dynamic, try dynamic fetch
                if has_react or has_spa_markers or has_minimal_content:
                    print(f"Detected dynamic content, switching to Playwright for {url}")
                    dynamic_content = asyncio.run(self.fetch_dynamic(url))
                    return dynamic_content if dynamic_content else content

            return content

        return None

    def get_soup(self, url: str, strategy: FetchStrategy = FetchStrategy.AUTO) -> Optional[BeautifulSoup]:
        """
        Fetch and parse content into BeautifulSoup object.

        Args:
            url: URL to fetch
            strategy: Fetching strategy to use

        Returns:
            BeautifulSoup object or None if failed
        """
        content = self.fetch(url, strategy)
        if content:
            return BeautifulSoup(content, 'lxml')
        return None

    def close(self):
        """Close the session."""
        self.session.close()
