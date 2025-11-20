"""Multi-strategy data extractor."""

import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag

from .utils import clean_text, extract_email, extract_phone, normalize_url


class DataExtractor:
    """Extracts structured data from HTML elements."""

    @staticmethod
    def extract_from_element(
        element: Tag,
        field_schema: Dict[str, str],
        base_url: str
    ) -> Dict[str, Any]:
        """
        Extract data from a single element based on field schema.

        Args:
            element: HTML element
            field_schema: Dictionary mapping field names to descriptions
            base_url: Base URL for link normalization

        Returns:
            Dictionary of extracted data
        """
        result = {}

        for field_name, field_description in field_schema.items():
            value = DataExtractor._extract_field(
                element, field_name, field_description, base_url
            )
            result[field_name] = value

        return result

    @staticmethod
    def _extract_field(
        element: Tag,
        field_name: str,
        field_description: str,
        base_url: str
    ) -> Optional[str]:
        """Extract a single field from an element."""

        # Special handling for common field types
        if 'email' in field_name.lower():
            return DataExtractor._extract_email_field(element)

        elif 'phone' in field_name.lower():
            return DataExtractor._extract_phone_field(element)

        elif 'url' in field_name.lower() or 'link' in field_name.lower():
            return DataExtractor._extract_url_field(element, base_url)

        elif 'image' in field_name.lower() or 'photo' in field_name.lower():
            return DataExtractor._extract_image_field(element, base_url)

        elif field_name.lower() in ['name', 'title', 'position', 'role']:
            return DataExtractor._extract_name_or_title(element)

        elif 'bio' in field_name.lower() or 'description' in field_name.lower():
            return DataExtractor._extract_bio(element)

        elif 'address' in field_name.lower() or 'location' in field_name.lower():
            return DataExtractor._extract_address(element)

        else:
            # Generic text extraction
            return DataExtractor._extract_generic_text(element, field_description)

    @staticmethod
    def _extract_email_field(element: Tag) -> Optional[str]:
        """Extract email from element."""
        # Look for mailto links
        mailto = element.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            email = mailto['href'].replace('mailto:', '').split('?')[0]
            return email.strip()

        # Look in text
        text = element.get_text()
        return extract_email(text)

    @staticmethod
    def _extract_phone_field(element: Tag) -> Optional[str]:
        """Extract phone from element."""
        # Look for tel links
        tel = element.find('a', href=re.compile(r'^tel:', re.I))
        if tel:
            phone = tel['href'].replace('tel:', '')
            return phone.strip()

        # Look in text
        text = element.get_text()
        return extract_phone(text)

    @staticmethod
    def _extract_url_field(element: Tag, base_url: str) -> Optional[str]:
        """Extract URL from element."""
        # Find first link
        link = element.find('a', href=True)
        if link:
            return normalize_url(base_url, link['href'])

        return None

    @staticmethod
    def _extract_image_field(element: Tag, base_url: str) -> Optional[str]:
        """Extract image URL from element."""
        # Find img tag
        img = element.find('img', src=True)
        if img:
            return normalize_url(base_url, img['src'])

        return None

    @staticmethod
    def _extract_name_or_title(element: Tag) -> Optional[str]:
        """Extract name or title."""
        # Try headings first
        for tag in ['h1', 'h2', 'h3', 'h4']:
            heading = element.find(tag)
            if heading:
                text = clean_text(heading.get_text())
                if text and len(text) < 200:
                    return text

        # Try elements with name/title classes
        for pattern in [r'name', r'title', r'heading']:
            named = element.find(['div', 'span', 'p'], {'class': re.compile(pattern, re.I)})
            if named:
                text = clean_text(named.get_text())
                if text and len(text) < 200:
                    return text

        # Try strong/bold text
        strong = element.find(['strong', 'b'])
        if strong:
            text = clean_text(strong.get_text())
            if text and len(text) < 200:
                return text

        # Try first link text
        link = element.find('a')
        if link:
            text = clean_text(link.get_text())
            if text and len(text) < 200:
                return text

        return None

    @staticmethod
    def _extract_bio(element: Tag) -> Optional[str]:
        """Extract biography or description."""
        # Look for bio/description elements
        for pattern in [r'bio', r'description', r'about', r'summary']:
            bio_el = element.find(['div', 'p', 'span'], {'class': re.compile(pattern, re.I)})
            if bio_el:
                text = clean_text(bio_el.get_text())
                if text and len(text) > 50:
                    return text

        # Get all paragraph text
        paragraphs = element.find_all('p')
        if paragraphs:
            bio_text = ' '.join([clean_text(p.get_text()) for p in paragraphs])
            if bio_text and len(bio_text) > 50:
                return bio_text

        # Fallback to all text if it's long enough
        all_text = clean_text(element.get_text())
        if len(all_text) > 100:
            return all_text[:1000]  # Limit length

        return None

    @staticmethod
    def _extract_address(element: Tag) -> Optional[str]:
        """Extract address or location."""
        # Look for address elements
        address = element.find('address')
        if address:
            return clean_text(address.get_text())

        # Look for location classes
        for pattern in [r'location', r'address', r'city', r'state']:
            loc = element.find(['div', 'span', 'p'], {'class': re.compile(pattern, re.I)})
            if loc:
                text = clean_text(loc.get_text())
                if text:
                    return text

        return None

    @staticmethod
    def _extract_generic_text(element: Tag, field_description: str) -> Optional[str]:
        """Generic text extraction based on keywords."""
        # Extract keywords from description
        keywords = re.findall(r'\b\w+\b', field_description.lower())

        # Try to find elements matching keywords
        for keyword in keywords:
            if len(keyword) < 3:
                continue

            # Look for class/id matching keyword
            found = element.find(['div', 'span', 'p'], {'class': re.compile(keyword, re.I)})
            if not found:
                found = element.find(['div', 'span', 'p'], {'id': re.compile(keyword, re.I)})

            if found:
                text = clean_text(found.get_text())
                if text:
                    return text

        # Fallback to first paragraph or text
        p = element.find('p')
        if p:
            return clean_text(p.get_text())

        return clean_text(element.get_text())[:500] if element.get_text() else None


class DetailPageExtractor:
    """Extracts data from detail pages."""

    @staticmethod
    def extract_from_page(
        soup: BeautifulSoup,
        field_schema: Dict[str, str],
        base_url: str
    ) -> Dict[str, Any]:
        """
        Extract data from a detail page.

        Args:
            soup: BeautifulSoup object
            field_schema: Field schema
            base_url: Base URL

        Returns:
            Extracted data
        """
        result = {}

        # Find main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', {'class': re.compile(r'content|main|profile|detail', re.I)}) or
            soup.find('body')
        )

        if not main_content:
            main_content = soup

        for field_name, field_description in field_schema.items():
            value = DataExtractor._extract_field(
                main_content, field_name, field_description, base_url
            )
            result[field_name] = value

        return result
