"""URL and structure analyzer for detecting patterns and pagination."""

import re
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urljoin
from collections import Counter

from bs4 import BeautifulSoup, Tag

from .utils import update_url_params, normalize_url


class StructureAnalyzer:
    """Analyzes page structure to detect patterns."""

    @staticmethod
    def find_repeating_elements(soup: BeautifulSoup) -> List[Tag]:
        """
        Find repeating elements that likely represent directory entries.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of repeating elements
        """
        # Common container patterns
        container_patterns = [
            ('div', {'class': re.compile(r'(card|item|entry|profile|person|member|result|listing)', re.I)}),
            ('li', {'class': re.compile(r'(item|entry|profile|person|member|result|listing)', re.I)}),
            ('tr', {}),
            ('article', {}),
            ('div', {'class': re.compile(r'row', re.I)}),
        ]

        best_candidates = []
        max_count = 0

        for tag_name, attrs in container_patterns:
            elements = soup.find_all(tag_name, attrs) if attrs else soup.find_all(tag_name)

            # Filter out navigation and footer elements
            elements = [
                el for el in elements
                if not any(parent.name in ['nav', 'footer', 'header'] for parent in el.parents)
            ]

            if len(elements) > max_count and len(elements) >= 3:
                max_count = len(elements)
                best_candidates = elements

        # Alternative: find by structural similarity
        if not best_candidates or len(best_candidates) < 3:
            best_candidates = StructureAnalyzer._find_by_structure_similarity(soup)

        return best_candidates

    @staticmethod
    def _find_by_structure_similarity(soup: BeautifulSoup, min_count: int = 3) -> List[Tag]:
        """Find elements with similar structure."""
        # Get all divs
        all_divs = soup.find_all(['div', 'li', 'article'])

        # Group by class signature
        class_groups = {}
        for div in all_divs:
            class_sig = ' '.join(sorted(div.get('class', [])))
            if class_sig:
                if class_sig not in class_groups:
                    class_groups[class_sig] = []
                class_groups[class_sig].append(div)

        # Find largest group
        for class_sig, elements in sorted(class_groups.items(), key=lambda x: len(x[1]), reverse=True):
            if len(elements) >= min_count:
                return elements

        return []

    @staticmethod
    def detect_pagination(soup: BeautifulSoup, current_url: str) -> Dict[str, Any]:
        """
        Detect pagination mechanism.

        Args:
            soup: BeautifulSoup object
            current_url: Current page URL

        Returns:
            Dictionary with pagination info
        """
        pagination_info = {
            'has_pagination': False,
            'type': None,  # 'url_param', 'path', 'button'
            'param_name': None,
            'total_pages': None,
            'next_url': None,
            'pattern': None
        }

        # Check URL parameters
        parsed = urlparse(current_url)
        query_params = parse_qs(parsed.query)

        # Common pagination parameters
        param_names = ['page', 'p', 'pg', 'pagenum', 'offset', 'start', 'from']

        for param in param_names:
            if param in query_params:
                pagination_info['has_pagination'] = True
                pagination_info['type'] = 'url_param'
                pagination_info['param_name'] = param
                break

        # Look for pagination links
        pagination_selectors = [
            soup.find('nav', {'class': re.compile(r'paginat', re.I)}),
            soup.find('div', {'class': re.compile(r'paginat', re.I)}),
            soup.find('ul', {'class': re.compile(r'paginat', re.I)}),
        ]

        for pagination_nav in pagination_selectors:
            if pagination_nav:
                pagination_info['has_pagination'] = True

                # Find next button/link
                next_link = (
                    pagination_nav.find('a', string=re.compile(r'next|»|›|>', re.I)) or
                    pagination_nav.find('a', {'class': re.compile(r'next', re.I)}) or
                    pagination_nav.find('a', {'rel': 'next'})
                )

                if next_link and next_link.get('href'):
                    pagination_info['next_url'] = normalize_url(current_url, next_link['href'])

                # Try to find total pages
                page_links = pagination_nav.find_all('a', href=True)
                page_numbers = []
                for link in page_links:
                    text = link.get_text(strip=True)
                    if text.isdigit():
                        page_numbers.append(int(text))

                if page_numbers:
                    pagination_info['total_pages'] = max(page_numbers)

                break

        # Check for "Load More" button
        load_more = soup.find(['button', 'a'], string=re.compile(r'load\s*more|show\s*more', re.I))
        if load_more:
            pagination_info['type'] = 'button'
            pagination_info['has_pagination'] = True

        return pagination_info

    @staticmethod
    def extract_links_from_elements(elements: List[Tag], base_url: str) -> List[str]:
        """
        Extract links from repeating elements.

        Args:
            elements: List of elements
            base_url: Base URL for normalization

        Returns:
            List of URLs
        """
        links = []

        for element in elements:
            # Find first link in element
            link = element.find('a', href=True)
            if link:
                href = link['href']
                # Filter out mailto:, tel:, javascript:, and # links
                if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                    # Try to find a different link
                    all_links = element.find_all('a', href=True)
                    for alt_link in all_links:
                        alt_href = alt_link['href']
                        if not alt_href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                            href = alt_href
                            break

                # Skip if still a special protocol
                if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                    continue

                url = normalize_url(base_url, href)
                # Filter out navigation links
                if '#' not in url.split('/')[-1]:  # Allow # in path but not fragment
                    links.append(url)

        return list(set(links))  # Remove duplicates

    @staticmethod
    def detect_detail_page_type(soup: BeautifulSoup) -> str:
        """
        Detect if this is a listing page or a detail page.

        Args:
            soup: BeautifulSoup object

        Returns:
            'listing' or 'detail'
        """
        # Check for repeating elements
        repeating = StructureAnalyzer.find_repeating_elements(soup)

        if len(repeating) >= 3:
            return 'listing'

        # Check for profile/detail indicators
        detail_indicators = [
            soup.find('div', {'class': re.compile(r'profile|bio|about|detail', re.I)}),
            soup.find('h1'),  # Detail pages usually have h1
            len(soup.get_text(strip=True)) > 1000  # More content
        ]

        if any(detail_indicators):
            return 'detail'

        return 'listing'


class PaginationHandler:
    """Handles pagination across different mechanisms."""

    @staticmethod
    def generate_pages(base_url: str, pagination_info: Dict[str, Any], max_pages: int = 100) -> List[str]:
        """
        Generate URLs for all pages.

        Args:
            base_url: Base URL
            pagination_info: Pagination information
            max_pages: Maximum pages to generate

        Returns:
            List of page URLs
        """
        if not pagination_info['has_pagination']:
            return [base_url]

        urls = [base_url]

        if pagination_info['type'] == 'url_param' and pagination_info['param_name']:
            param = pagination_info['param_name']

            # Determine the number of pages
            if pagination_info['total_pages']:
                num_pages = min(pagination_info['total_pages'], max_pages)
            else:
                num_pages = max_pages

            # Generate URLs
            for page_num in range(2, num_pages + 1):
                page_url = update_url_params(base_url, {param: page_num})
                urls.append(page_url)

        elif pagination_info['next_url']:
            # Follow next links (will need to be done iteratively)
            urls.append(pagination_info['next_url'])

        return urls

    @staticmethod
    def extract_page_number_from_url(url: str) -> Optional[int]:
        """Extract current page number from URL."""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        param_names = ['page', 'p', 'pg', 'pagenum']

        for param in param_names:
            if param in query_params:
                try:
                    return int(query_params[param][0])
                except:
                    pass

        return None
