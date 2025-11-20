"""Main directory scraper orchestrator."""

import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from .fetcher import ContentFetcher, FetchStrategy
from .analyzer import StructureAnalyzer, PaginationHandler
from .extractor import DataExtractor, DetailPageExtractor
from .llm_extractor import LLMExtractor
from .utils import normalize_url


class DirectoryScraper:
    """Main scraper that orchestrates the scraping process."""

    def __init__(
        self,
        use_llm: bool = False,
        llm_api_key: Optional[str] = None,
        max_workers: int = 5,
        timeout: int = 30,
        max_pages: int = 100,
        verbose: bool = True
    ):
        """
        Initialize the scraper.

        Args:
            use_llm: Whether to use LLM for extraction
            llm_api_key: OpenAI API key
            max_workers: Maximum concurrent workers
            timeout: Request timeout
            max_pages: Maximum pages to scrape
            verbose: Print progress
        """
        self.fetcher = ContentFetcher(timeout=timeout)
        self.llm_extractor = LLMExtractor(api_key=llm_api_key) if use_llm else None
        self.max_workers = max_workers
        self.max_pages = max_pages
        self.verbose = verbose

    def scrape(
        self,
        url: str,
        field_schema: Dict[str, str],
        fetch_strategy: FetchStrategy = FetchStrategy.AUTO
    ) -> List[Dict[str, Any]]:
        """
        Scrape a directory URL and extract structured data.

        Args:
            url: Directory URL to scrape
            field_schema: Dictionary mapping field names to descriptions
            fetch_strategy: Fetching strategy

        Returns:
            List of extracted data dictionaries
        """
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Scraping: {url}")
            print(f"{'='*60}\n")

        # Fetch the initial page
        soup = self.fetcher.get_soup(url, strategy=fetch_strategy)
        if not soup:
            print(f"Failed to fetch {url}")
            return []

        # Analyze page type
        page_type = StructureAnalyzer.detect_detail_page_type(soup)

        if self.verbose:
            print(f"Page type detected: {page_type}")

        if page_type == 'detail':
            # Single detail page
            return [self._extract_from_detail_page(soup, field_schema, url)]

        else:
            # Listing page - scrape all pages and entries
            return self._scrape_listing_pages(url, field_schema, soup, fetch_strategy)

    def _scrape_listing_pages(
        self,
        base_url: str,
        field_schema: Dict[str, str],
        initial_soup,
        fetch_strategy: FetchStrategy
    ) -> List[Dict[str, Any]]:
        """Scrape all pages from a listing directory."""

        all_results = []

        # Detect pagination
        pagination_info = StructureAnalyzer.detect_pagination(initial_soup, base_url)

        if self.verbose:
            print(f"Pagination detected: {pagination_info['has_pagination']}")

        # Generate page URLs
        if pagination_info['has_pagination']:
            page_urls = PaginationHandler.generate_pages(base_url, pagination_info, self.max_pages)
        else:
            page_urls = [base_url]

        if self.verbose:
            print(f"Pages to scrape: {len(page_urls)}")

        # Scrape each page
        for page_num, page_url in enumerate(page_urls, 1):
            if self.verbose:
                print(f"\nScraping page {page_num}/{len(page_urls)}: {page_url}")

            # Use cached soup for first page
            if page_url == base_url and initial_soup:
                soup = initial_soup
            else:
                soup = self.fetcher.get_soup(page_url, strategy=fetch_strategy)

                if not soup:
                    print(f"Failed to fetch page {page_num}")
                    continue

                # Be respectful - rate limit
                time.sleep(1)

            # Extract from this page
            page_results = self._extract_from_listing_page(
                soup, field_schema, page_url, fetch_strategy
            )

            all_results.extend(page_results)

            if self.verbose:
                print(f"Extracted {len(page_results)} entries from page {page_num}")

            # Check if we should stop (no more results)
            if not page_results and page_num > 1:
                print("No more results found, stopping pagination")
                break

        return all_results

    def _extract_from_listing_page(
        self,
        soup,
        field_schema: Dict[str, str],
        page_url: str,
        fetch_strategy: FetchStrategy
    ) -> List[Dict[str, Any]]:
        """Extract data from a single listing page."""

        # Find repeating elements
        elements = StructureAnalyzer.find_repeating_elements(soup)

        if not elements:
            if self.verbose:
                print("No repeating elements found")
            return []

        if self.verbose:
            print(f"Found {len(elements)} repeating elements")

        # Check if elements contain links to detail pages
        links = StructureAnalyzer.extract_links_from_elements(elements, page_url)

        if links and len(links) >= len(elements) * 0.5:
            # Likely links to detail pages
            if self.verbose:
                print(f"Found {len(links)} detail page links")

            return self._scrape_detail_pages(links, field_schema, fetch_strategy)

        else:
            # Extract directly from listing elements
            if self.verbose:
                print("Extracting directly from listing elements")

            return self._extract_from_elements(elements, field_schema, page_url)

    def _extract_from_elements(
        self,
        elements,
        field_schema: Dict[str, str],
        base_url: str
    ) -> List[Dict[str, Any]]:
        """Extract data directly from listing elements."""

        results = []

        for element in elements:
            data = DataExtractor.extract_from_element(element, field_schema, base_url)

            # Use LLM if enabled and data is incomplete
            if self.llm_extractor:
                missing_fields = sum(1 for v in data.values() if not v)
                if missing_fields > len(data) * 0.3:  # More than 30% missing
                    html = str(element)
                    data = self.llm_extractor.smart_extract(html, field_schema, data)

            results.append(data)

        return results

    def _scrape_detail_pages(
        self,
        urls: List[str],
        field_schema: Dict[str, str],
        fetch_strategy: FetchStrategy
    ) -> List[Dict[str, Any]]:
        """Scrape multiple detail pages concurrently."""

        results = []

        # Use ThreadPoolExecutor for concurrent scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._scrape_single_detail_page,
                    url,
                    field_schema,
                    fetch_strategy
                ): url
                for url in urls
            }

            # Process completed futures with progress bar
            if self.verbose:
                pbar = tqdm(total=len(futures), desc="Scraping detail pages")

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    url = futures[future]
                    print(f"Error scraping {url}: {e}")

                if self.verbose:
                    pbar.update(1)

                # Rate limiting
                time.sleep(0.5)

            if self.verbose:
                pbar.close()

        return results

    def _scrape_single_detail_page(
        self,
        url: str,
        field_schema: Dict[str, str],
        fetch_strategy: FetchStrategy
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single detail page."""

        soup = self.fetcher.get_soup(url, strategy=fetch_strategy)

        if not soup:
            return None

        return self._extract_from_detail_page(soup, field_schema, url)

    def _extract_from_detail_page(
        self,
        soup,
        field_schema: Dict[str, str],
        url: str
    ) -> Dict[str, Any]:
        """Extract data from a detail page."""

        data = DetailPageExtractor.extract_from_page(soup, field_schema, url)

        # Add page URL if in schema
        if 'page_url' in field_schema or 'url' in field_schema:
            url_field = 'page_url' if 'page_url' in field_schema else 'url'
            data[url_field] = url

        # Use LLM if enabled and data is incomplete
        if self.llm_extractor:
            missing_fields = sum(1 for v in data.values() if not v)
            if missing_fields > len(data) * 0.3:  # More than 30% missing
                html = str(soup)
                data = self.llm_extractor.smart_extract(html, field_schema, data)

        return data

    def close(self):
        """Clean up resources."""
        self.fetcher.close()


def scrape_directory(
    url: str,
    field_schema: Dict[str, str],
    use_llm: bool = False,
    llm_api_key: Optional[str] = None,
    max_workers: int = 5,
    max_pages: int = 100,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape a directory.

    Args:
        url: Directory URL
        field_schema: Field schema
        use_llm: Use LLM for extraction
        llm_api_key: OpenAI API key
        max_workers: Max concurrent workers
        max_pages: Max pages to scrape
        verbose: Print progress

    Returns:
        List of extracted data
    """
    scraper = DirectoryScraper(
        use_llm=use_llm,
        llm_api_key=llm_api_key,
        max_workers=max_workers,
        max_pages=max_pages,
        verbose=verbose
    )

    try:
        return scraper.scrape(url, field_schema)
    finally:
        scraper.close()
