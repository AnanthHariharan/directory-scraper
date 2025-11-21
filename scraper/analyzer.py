"""URL and structure analyzer for detecting patterns and pagination."""

import re
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs, urljoin
from collections import Counter

from bs4 import BeautifulSoup, Tag

from .utils import update_url_params, normalize_url, clean_text


class StructureAnalyzer:
    """Analyzes page structure to detect patterns."""

    @staticmethod
    def extract_table_headers(row: Tag) -> Optional[List[str]]:
        """
        Extract table headers associated with a row.

        Args:
            row: Table row element

        Returns:
            List of header strings or None
        """
        table = row.find_parent('table')
        if not table:
            return None
            
        # Look for thead
        thead = table.find('thead')
        if thead:
            headers = thead.find_all('th')
            if headers:
                return [clean_text(h.get_text()) for h in headers]
                
        # Look for first row if it has th
        first_row = table.find('tr')
        if first_row:
            headers = first_row.find_all('th')
            if headers:
                return [clean_text(h.get_text()) for h in headers]
                
        # Look for first row if it's not the current row (and current row is not header)
        # This is risky if the table has no headers, but we can check if first row is bold or different style
        # For now, stick to explicit headers
                
        return None

    @staticmethod
    def find_repeating_elements(soup: BeautifulSoup) -> List[Tag]:
        """
        Find repeating elements that likely represent directory entries.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of repeating elements
        """
        # Common container patterns (ordered by priority)
        container_patterns = [
            # High-priority specific patterns
            ('div', {'class': re.compile(r'(person|member|profile|employee|staff|student|faculty|directory-item)', re.I)}),
            ('li', {'class': re.compile(r'(person|member|profile|employee|staff|student|faculty|directory-item)', re.I)}),
            ('article', {'class': re.compile(r'(person|member|profile|employee|staff|student|faculty|directory-item)', re.I)}),
            
            # Table rows (common for directories)
            ('tr', {}),

            # Medium-priority patterns
            ('div', {'class': re.compile(r'(card|entry|result|listing|item|row|col)', re.I)}),
            ('li', {'class': re.compile(r'(entry|result|listing|item)', re.I)}),
            ('article', {}),
            
            # Generic containers that might be repeated
            ('div', {'class': True}),
            ('li', {}),
        ]

        best_candidates = []
        max_count = 0
        max_score = 0

        # Strategy 1: Pattern matching
        for tag_name, attrs in container_patterns:
            raw_elements = soup.find_all(tag_name, attrs) if attrs else soup.find_all(tag_name)
            
            # Filter out navigation, footer, header, and menu elements
            elements = [
                el for el in raw_elements
                if not any(parent.name in ['nav', 'footer', 'header'] for parent in el.parents)
                and not any('nav' in parent.get('class', []) or 'menu' in parent.get('class', []) 
                           for parent in el.parents if hasattr(parent, 'get'))
                and not StructureAnalyzer._is_navigation_element(el)
            ]

            candidate_sets = []

            # Special handling for TRs: group by parent table
            if tag_name == 'tr' and not attrs:
                tables = {}
                for tr in elements:
                    parent = tr.find_parent('table')
                    if parent:
                        if parent not in tables:
                            tables[parent] = []
                        tables[parent].append(tr)
                
                candidate_sets.extend(list(tables.values()))
            else:
                candidate_sets.append(elements)

            for candidate_elements in candidate_sets:
                if len(candidate_elements) >= 3:
                    # Score elements based on content richness
                    score = StructureAnalyzer._score_elements(candidate_elements)
                    
                    # Prefer high-scoring sets with good counts
                    # We weight score more heavily than count to avoid picking up small UI elements
                    weighted_score = score * (min(len(candidate_elements), 20) / 20.0)
                    
                    if weighted_score > max_score:
                        max_score = weighted_score
                        max_count = len(candidate_elements)
                        best_candidates = candidate_elements

        # Strategy 2: Structural similarity (Fallback)
        if not best_candidates or max_score < 10:
            structure_candidates = StructureAnalyzer._find_by_structure_similarity(soup)
            if structure_candidates:
                structure_score = StructureAnalyzer._score_elements(structure_candidates)
                if structure_score > max_score:
                    best_candidates = structure_candidates

        # For table rows, exclude header rows
        if best_candidates and best_candidates[0].name == 'tr':
            best_candidates = StructureAnalyzer._filter_table_headers(best_candidates)

        return best_candidates

    @staticmethod
    def _is_navigation_element(element: Tag) -> bool:
        """Check if element is likely a navigation item."""
        # Check element's own classes
        classes = ' '.join(element.get('class', [])).lower()
        nav_keywords = ['nav', 'menu', 'header', 'footer', 'sidebar', 'breadcrumb', 'pagination']
        
        if any(keyword in classes for keyword in nav_keywords):
            return True

        # Check if text is very short (likely navigation)
        text = element.get_text(strip=True)
        if len(text) < 10 and element.find_all(['a']) and not element.find_all(['p', 'div']):
            return True

        # Check for common navigation text
        nav_text = ['home', 'about', 'contact', 'login', 'sign in', 'menu', 'search', 'next', 'prev']
        if text.lower() in nav_text:
            return True

        return False

    @staticmethod
    def _score_elements(elements: List[Tag]) -> int:
        """Score a set of elements based on content richness."""
        if not elements:
            return 0

        # Sample first few elements
        sample = elements[:min(5, len(elements))]
        total_score = 0

        for el in sample:
            score = 0
            
            # Has email link
            if el.find('a', href=re.compile(r'mailto:', re.I)):
                score += 15
            
            # Has phone link
            if el.find('a', href=re.compile(r'tel:', re.I)):
                score += 15
                
            # Has regular links
            links = el.find_all('a', href=True)
            if links:
                score += min(len(links) * 3, 15)

            # Has text content
            text = el.get_text(strip=True)
            if 20 < len(text) < 1000:
                score += 10
            elif len(text) >= 1000:
                score += 5  # Too long might be wrong element
            
            # Has images
            if el.find('img'):
                score += 5

            # Has structured content (multiple children)
            children = [c for c in el.children if hasattr(c, 'name')]
            if 2 <= len(children) <= 30:
                score += 10
                
            # Consistency check: does it look like a list item?
            if el.name == 'li':
                score += 5
            elif el.name == 'tr':
                score += 5

            total_score += score

        return total_score // len(sample)

    @staticmethod
    def _filter_table_headers(rows: List[Tag]) -> List[Tag]:
        """Filter out table header rows."""
        if not rows:
            return rows

        # Check first few rows for header-like properties
        filtered_rows = []
        for i, row in enumerate(rows[:3]):
            is_header = False
            
            # Has <th> tags instead of <td>
            if row.find_all('th'):
                is_header = True
            
            # Check if text suggests it's a header
            text = row.get_text(strip=True).lower()
            header_keywords = ['name', 'email', 'phone', 'title', 'position', 'department', 'role', 'contact']
            
            # If row contains multiple header keywords and no links, likely a header
            keyword_count = sum(1 for keyword in header_keywords if keyword in text)
            if keyword_count >= 2 and not row.find_all('a', href=re.compile(r'mailto:|tel:', re.I)):
                is_header = True
                
            if not is_header:
                filtered_rows.extend(rows[i:])
                break
                
        return filtered_rows if filtered_rows else rows

    @staticmethod
    def _find_by_structure_similarity(soup: BeautifulSoup, min_count: int = 3) -> List[Tag]:
        """Find elements with similar structure."""
        # Get all potential containers
        candidates = soup.find_all(['div', 'li', 'article', 'section', 'tr'])
        
        # Group by tag signature (tag name + direct children tags)
        structure_groups = {}
        
        for el in candidates:
            # Skip tiny elements
            if len(el.get_text(strip=True)) < 10:
                continue
                
            # Create a signature based on tag name and children types
            children_sig = tuple(sorted([child.name for child in el.children if hasattr(child, 'name') and child.name]))
            signature = (el.name, children_sig)
            
            if signature not in structure_groups:
                structure_groups[signature] = []
            structure_groups[signature].append(el)

        # Find best group
        best_group = []
        max_score = 0
        
        for signature, elements in structure_groups.items():
            if len(elements) >= min_count:
                score = StructureAnalyzer._score_elements(elements)
                # Weight by number of elements but cap it
                weighted_score = score * (min(len(elements), 50) / 10.0)
                
                if weighted_score > max_score:
                    max_score = weighted_score
                    best_group = elements
                    
        return best_group

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
