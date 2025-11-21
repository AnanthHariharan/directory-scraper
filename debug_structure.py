#!/usr/bin/env python3
"""Debug script to examine HTML structure of failing pages."""

import requests
from bs4 import BeautifulSoup
from scraper.analyzer import StructureAnalyzer

def debug_page(url, title):
    """Debug a single page's structure."""
    print(f"\n{'=' * 80}")
    print(f"Debugging: {title}")
    print(f"URL: {url}")
    print(f"{'=' * 80}\n")

    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(response.content, 'lxml')

    # Find repeating elements
    repeating = StructureAnalyzer.find_repeating_elements(soup)

    print(f"Found {len(repeating)} repeating elements")
    print(f"\nFirst 3 repeating elements:")
    print("-" * 80)

    for i, elem in enumerate(repeating[:3]):
        print(f"\n[Element {i+1}]")
        print(f"Tag: {elem.name}")
        print(f"Classes: {elem.get('class', [])}")
        print(f"Text (first 200 chars): {elem.get_text(strip=True)[:200]}")

        # Check for links
        links = elem.find_all('a', href=True)
        print(f"Links found: {len(links)}")
        if links:
            for link in links[:3]:
                print(f"  - {link.get('href')} : {link.get_text(strip=True)[:50]}")

        # Check for emails
        emails = elem.find_all('a', href=lambda x: x and x.startswith('mailto:'))
        if emails:
            print(f"Email links: {[e['href'] for e in emails]}")

        # Check for table headers
        if elem.name == 'tr':
            headers = StructureAnalyzer.extract_table_headers(elem)
            print(f"Table Headers: {headers}")

        print("-" * 40)

# Test on failing pages
debug_page("https://sais.health.pa.gov/commonpoc/content/publicweb/nhinformation2.asp?COUNTY=Allegheny", "Pennsylvania Health")

