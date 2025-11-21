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

        # Check if this is a table row - use table-aware extraction
        if element.name == 'tr':
            result = DataExtractor._extract_from_table_row(element, field_schema, base_url)
        else:
            for field_name, field_description in field_schema.items():
                value = DataExtractor._extract_field(
                    element, field_name, field_description, base_url
                )
                result[field_name] = value

        return result

    @staticmethod
    def extract_from_table_row_with_headers(
        row: Tag,
        field_schema: Dict[str, str],
        base_url: str,
        headers: List[str]
    ) -> Dict[str, Any]:
        """
        Extract data from a table row using headers to map columns.

        Args:
            row: Table row element
            field_schema: Field schema
            base_url: Base URL
            headers: List of table headers

        Returns:
            Extracted data
        """
        result = {}
        cells = row.find_all(['td', 'th'])

        if not cells:
            return DataExtractor._extract_from_table_row(row, field_schema, base_url)

        # Map headers to schema fields
        col_to_fields = {}  # col_idx -> List[field_name]
        
        for col_idx, header in enumerate(headers):
            if col_idx >= len(cells):
                break
                
            header_lower = header.lower()
            
            # Find all matching fields
            for field_name, field_desc in field_schema.items():
                score = 0
                name_lower = field_name.lower()
                
                # Exact match
                if name_lower == header_lower:
                    score = 100
                # Header contains field name (e.g. "Employee Name" -> "name")
                elif name_lower in header_lower:
                    score = 80
                # Field name contains header
                elif header_lower in name_lower:
                    score = 60
                
                # Common synonyms
                if 'email' in header_lower and 'email' in name_lower:
                    score = 90
                elif 'phone' in header_lower and 'phone' in name_lower:
                    score = 90
                elif ('address' in header_lower or 'location' in header_lower) and ('address' in name_lower or 'location' in name_lower):
                    score = 90
                elif ('link' in header_lower or 'website' in header_lower) and ('url' in name_lower or 'website' in name_lower):
                    score = 90
                elif ('type' in header_lower or 'category' in header_lower) and ('type' in name_lower or 'category' in name_lower):
                    score = 90
                    
                if score > 50:
                    if col_idx not in col_to_fields:
                        col_to_fields[col_idx] = []
                    col_to_fields[col_idx].append(field_name)

        # Extract data
        for col_idx, cell in enumerate(cells):
            if col_idx in col_to_fields:
                for field_name in col_to_fields[col_idx]:
                    # Extract specific field from this cell
                    value = DataExtractor._extract_field(cell, field_name, field_schema[field_name], base_url)
                    
                    if value:
                        if field_name in result and result[field_name]:
                            # Append if already exists
                            if value not in result[field_name]: # Avoid duplicates
                                result[field_name] += " " + value
                        else:
                            result[field_name] = value

        # Fill missing fields with None (or try fallback extraction?)
        # If we missed important fields, maybe we should try the heuristic extraction for those specific fields on unmapped cells?
        # But let's trust the headers first.
        
        for field_name in field_schema:
            if field_name not in result:
                result[field_name] = None

        return result

    @staticmethod
    def _extract_from_table_row(
        row: Tag,
        field_schema: Dict[str, str],
        base_url: str
    ) -> Dict[str, Any]:
        """
        Extract data from a table row intelligently.

        Args:
            row: Table row element
            field_schema: Field schema
            base_url: Base URL

        Returns:
            Extracted data
        """
        result = {}

        # Get all cells
        cells = row.find_all(['td', 'th'])

        if not cells:
            # Fallback to regular extraction
            for field_name, field_description in field_schema.items():
                value = DataExtractor._extract_field(row, field_name, field_description, base_url)
                result[field_name] = value
            return result

        # Try to intelligently map cells to fields
        # Common patterns: name, title/position, email, phone, etc.

        field_names = list(field_schema.keys())

        # Strategy 1: Map by cell content type
        cell_assignments = {}

        for i, cell in enumerate(cells):
            # Check what type of data this cell contains
            cell_text = clean_text(cell.get_text())

            # Email detection
            if 'email' in field_names and 'email' not in cell_assignments:
                email_link = cell.find('a', href=re.compile(r'mailto:', re.I))
                if email_link or extract_email(cell_text):
                    cell_assignments['email'] = i
                    continue

            # Phone detection
            if 'phone' in field_names and 'phone' not in cell_assignments:
                phone_link = cell.find('a', href=re.compile(r'tel:', re.I))
                if phone_link or extract_phone(cell_text):
                    cell_assignments['phone'] = i
                    continue

            # URL detection
            url_field = next((f for f in field_names if 'url' in f.lower() or 'link' in f.lower() or 'website' in f.lower()), None)
            if url_field and url_field not in cell_assignments:
                link = cell.find('a', href=True)
                if link and not link['href'].startswith(('mailto:', 'tel:', '#')):
                    cell_assignments[url_field] = i
                    continue

        # Strategy 2: Assign remaining fields by position
        assigned_cells = set(cell_assignments.values())

        for i, cell in enumerate(cells):
            if i in assigned_cells:
                continue

            cell_text = clean_text(cell.get_text())
            if not cell_text or len(cell_text) < 2:
                continue

            # Find first unassigned field
            for field_name in field_names:
                if field_name in cell_assignments:
                    continue

                # Name/title usually comes first
                if field_name.lower() in ['name', 'title', 'position', 'role']:
                    # Should be reasonable length text
                    if 2 < len(cell_text) < 200:
                        cell_assignments[field_name] = i
                        assigned_cells.add(i)
                        break

                # Bio/description usually longer
                elif 'bio' in field_name.lower() or 'description' in field_name.lower():
                    if len(cell_text) > 50:
                        cell_assignments[field_name] = i
                        assigned_cells.add(i)
                        break

                # Generic fields
                else:
                    cell_assignments[field_name] = i
                    assigned_cells.add(i)
                    break

        # Extract values based on assignments
        for field_name in field_names:
            if field_name in cell_assignments:
                cell_index = cell_assignments[field_name]
                if cell_index < len(cells):
                    cell = cells[cell_index]
                    value = DataExtractor._extract_field(cell, field_name, field_schema[field_name], base_url)
                    result[field_name] = value
                else:
                    result[field_name] = None
            else:
                # Try regular extraction on the whole row
                value = DataExtractor._extract_field(row, field_name, field_schema[field_name], base_url)
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
            return DataExtractor._extract_generic_text(element, field_description, field_name)

    @staticmethod
    def _extract_email_field(element: Tag) -> Optional[str]:
        """Extract email from element."""
        # Look for mailto links (recursive)
        mailto = element.find('a', href=re.compile(r'^mailto:', re.I))
        if mailto:
            email = mailto['href'].replace('mailto:', '').split('?')[0].strip()
            if email and '@' in email:
                return email

        # Look in data attributes
        for attr in ['data-email', 'data-mail', 'data-contact']:
            if element.get(attr):
                email = element[attr].strip()
                if email and '@' in email:
                    return email

        # Look in nested elements with email-related classes
        for pattern in [r'email', r'mail', r'contact']:
            email_el = element.find(['span', 'div', 'p', 'td'], {'class': re.compile(pattern, re.I)})
            if email_el:
                email = extract_email(email_el.get_text())
                if email:
                    return email

        # Look in all links (sometimes email is in href without mailto:)
        links = element.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if '@' in href and '.' in href and not href.startswith(('http:', 'https:', 'tel:', 'javascript:')):
                return href.strip()
            # Check link text
            text = link.get_text(strip=True)
            if extract_email(text):
                return extract_email(text)

        # Look in text content (recursive but limited depth to avoid performance hit)
        text = element.get_text()
        email = extract_email(text)
        if email:
            return email

        return None

    @staticmethod
    def _extract_phone_field(element: Tag) -> Optional[str]:
        """Extract phone from element."""
        # Look for tel links
        tel = element.find('a', href=re.compile(r'^tel:', re.I))
        if tel:
            phone = tel['href'].replace('tel:', '').replace('+1', '').strip()
            if phone:
                return phone

        # Look in data attributes
        for attr in ['data-phone', 'data-tel', 'data-telephone']:
            if element.get(attr):
                phone = element[attr].strip()
                if phone:
                    return phone

        # Look in nested elements with phone-related classes
        for pattern in [r'\bphone\b', r'\btel\b', r'\btelephone\b', r'\bcontact\b', r'\bcall\b', r'\bmobile\b', r'\bcell\b']:
            phone_el = element.find(['span', 'div', 'p', 'td', 'a'], {'class': re.compile(pattern, re.I)})
            if phone_el:
                phone = extract_phone(phone_el.get_text())
                if phone:
                    return phone

        # Look for text near "Phone:" label
        label_match = re.search(r'(?:phone|tel|mobile|cell|contact)\s*:?\s*([+\d\s\-\(\)\.]+)', element.get_text(), re.I)
        if label_match:
            potential_phone = label_match.group(1).strip()
            if extract_phone(potential_phone):
                return potential_phone

        # Look in all text content
        text = element.get_text()
        phone = extract_phone(text)
        if phone:
            return phone

        return None

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
            
        # Look for background image in style
        style = element.get('style', '')
        if 'background-image' in style:
            match = re.search(r'url\([\'"]?([^\'"\)]+)[\'"]?\)', style)
            if match:
                return normalize_url(base_url, match.group(1))

        return None

    @staticmethod
    def _extract_name_or_title(element: Tag) -> Optional[str]:
        """Extract name or title."""
        # Try headings first
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
            heading = element.find(tag)
            if heading:
                text = clean_text(heading.get_text())
                if text and 2 < len(text) < 200:
                    return text

        # Try elements with name/title classes
        for pattern in [r'\bname\b', r'\btitle\b', r'\bheading\b', r'\blabel\b', r'\bheader\b']:
            named = element.find(['div', 'span', 'p', 'td', 'th', 'strong', 'b'], {'class': re.compile(pattern, re.I)})
            if named:
                text = clean_text(named.get_text())
                if text and 2 < len(text) < 200:
                    return text

        # Try strong/bold text (but not if it's just a label)
        strong = element.find(['strong', 'b'])
        if strong:
            text = clean_text(strong.get_text())
            if text and 2 < len(text) < 200 and not text.endswith(':'):
                return text

        # Try first link text (but not mailto/tel links)
        links = element.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            if not href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                text = clean_text(link.get_text())
                if text and 2 < len(text) < 200:
                    return text

        # Try data attributes
        for attr in ['data-name', 'data-title']:
            if element.get(attr):
                text = clean_text(element[attr])
                if text and 2 < len(text) < 200:
                    return text

        # Fallback: Get first substantial text node (but filter out common noise)
        direct_text = DataExtractor._get_direct_text(element)
        if direct_text and 2 < len(direct_text) < 200:
            # Don't return if it looks like an email or phone
            if not extract_email(direct_text) and not extract_phone(direct_text):
                return direct_text

        return None

    @staticmethod
    def _get_direct_text(element: Tag) -> Optional[str]:
        """Get direct text content, excluding nested tags."""
        if not element:
            return None

        # Get all text, but try to find the most prominent/first text
        texts = []

        for child in element.children:
            if isinstance(child, str):
                text = clean_text(child)
                if text:
                    texts.append(text)
            elif hasattr(child, 'get_text'):
                # If child is a small inline element (span, b, i), treat as text
                if child.name in ['span', 'b', 'i', 'strong', 'em', 'small']:
                    text = clean_text(child.get_text())
                    if text:
                        texts.append(text)

        if texts:
            # Return longest or first substantial text
            substantial = [t for t in texts if len(t) > 2]
            if substantial:
                return substantial[0]

        return None

    @staticmethod
    def _extract_bio(element: Tag) -> Optional[str]:
        """Extract biography or description."""
        # Look for bio/description elements
        for pattern in [r'bio', r'description', r'about', r'summary', r'content']:
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
            text = clean_text(address.get_text())
            if text:
                return text

        # Look for data attributes
        for attr in ['data-address', 'data-location', 'data-city']:
            if element.get(attr):
                text = clean_text(element[attr])
                if text:
                    return text

        # Look for location classes (more comprehensive patterns)
        for pattern in [r'\blocation\b', r'\baddress\b', r'\bcity\b', r'\bstate\b', r'\bregion\b',
                       r'\barea\b', r'\blocale\b', r'\bplace\b', r'\boffice\b']:
            loc = element.find(['div', 'span', 'p', 'td'], {'class': re.compile(pattern, re.I)})
            if loc:
                text = clean_text(loc.get_text())
                if text and len(text) > 3:
                    return text

        # Look for itemprop address (schema.org markup)
        schema_addr = element.find(['div', 'span'], {'itemprop': re.compile(r'address|location', re.I)})
        if schema_addr:
            text = clean_text(schema_addr.get_text())
            if text:
                return text

        # Look for common address patterns in text
        text = element.get_text()
        # Look for city, state patterns
        city_state_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})'
        match = re.search(city_state_pattern, text)
        if match:
            return match.group(0)

        # Look for street address patterns
        street_pattern = r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way)'
        match = re.search(street_pattern, text, re.I)
        if match:
            # Try to get more context
            return match.group(0)

        return None

    @staticmethod
    def _extract_generic_text(element: Tag, field_description: str, field_name: str = "") -> Optional[str]:
        """Generic text extraction based on keywords."""
        # Extract keywords from description and name
        keywords = re.findall(r'\b\w+\b', field_description.lower())
        if field_name:
            keywords.extend(re.findall(r'\b\w+\b', field_name.lower()))
            
        significant_keywords = [k for k in keywords if len(k) >= 3 and k not in
                               ['the', 'and', 'for', 'that', 'with', 'from', 'extract', 'get', 'find']]
        
        # Remove duplicates
        significant_keywords = list(set(significant_keywords))

        # Try to find elements matching keywords
        for keyword in significant_keywords:
            # Look for class/id matching keyword
            found = element.find(['div', 'span', 'p', 'td', 'dd', 'li'], {'class': re.compile(keyword, re.I)})
            if not found:
                found = element.find(['div', 'span', 'p', 'td', 'dd', 'li'], {'id': re.compile(keyword, re.I)})

            if found:
                text = clean_text(found.get_text())
                if text and len(text) > 2:
                    return text

            # Look for data attributes
            data_attr = f'data-{keyword}'
            if element.get(data_attr):
                text = clean_text(element[data_attr])
                if text:
                    return text
                    
            # Look for text near label (e.g. "Department: Math")
            label_pattern = re.compile(f"{keyword}\\s*[:\\-]\\s*([^\\n<]+)", re.I)
            text_content = element.get_text()
            match = label_pattern.search(text_content)
            if match:
                return match.group(1).strip()

        # Try common semantic HTML
        for tag in ['dd', 'blockquote', 'p', 'span']:
            el = element.find(tag)
            if el:
                text = clean_text(el.get_text())
                if text and len(text) > 2:
                    return text

        # Fallback to all text, but clean it
        all_text = clean_text(element.get_text())
        if all_text and len(all_text) > 2:
            return all_text[:500]

        return None


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
