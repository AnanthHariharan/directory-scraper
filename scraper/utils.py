"""Utility functions for the scraper."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import hashlib


def normalize_url(base_url: str, url: str) -> str:
    """Normalize and join URLs."""
    if not url:
        return base_url
    return urljoin(base_url, url.strip())


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters
    text = text.strip()
    return text


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    if not text:
        return None

    # More comprehensive email pattern
    email_pattern = r'\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}\b'
    match = re.search(email_pattern, text)

    if match:
        email = match.group(0)
        # Clean up common issues
        email = email.strip('.')
        return email

    return None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from text."""
    if not text:
        return None

    # Try multiple phone patterns (US-centric but flexible)
    patterns = [
        # (123) 456-7890 or 123-456-7890 or 123.456.7890
        r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        # 1234567890
        r'\b([0-9]{10})\b',
        # +1 123 456 7890
        r'\b\+?1?\s*\(?([0-9]{3})\)?\s*([0-9]{3})\s*([0-9]{4})\b'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = match.group(0)
            # Normalize: remove common separators but keep the digits
            return phone.strip()

    return None


def get_url_hash(url: str) -> str:
    """Generate a hash for a URL."""
    return hashlib.md5(url.encode()).hexdigest()


def update_url_params(url: str, params: Dict[str, Any]) -> str:
    """Update URL parameters."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Update with new params
    for key, value in params.items():
        query_params[key] = [str(value)]

    # Rebuild URL
    new_query = urlencode(query_params, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def detect_pagination_pattern(url: str) -> Optional[str]:
    """Detect pagination parameter in URL."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # Common pagination parameters
    pagination_params = ['page', 'p', 'pg', 'pagenum', 'offset', 'start']

    for param in pagination_params:
        if param in query_params:
            return param

    return None


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
