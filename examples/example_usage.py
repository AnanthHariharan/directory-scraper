"""Example usage of the directory scraper."""

import json
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import DirectoryScraper
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def example_stanford_engineering():
    """Example: Scrape Stanford Engineering profiles."""
    print("\n" + "="*60)
    print("Example 1: Stanford Engineering Profiles")
    print("="*60)

    url = "https://profiles.stanford.edu/browse/school-of-engineering?p=1&ps=100"

    field_schema = {
        "name": "name of the person",
        "title": "their title or position, e.g. Postdoctoral Scholar, Bioengineering",
        "email": "their email address",
        "page_url": "url of their profile page",
        "bio": "their biography or research interests"
    }

    scraper = DirectoryScraper(
        use_llm=False,  # Start without LLM
        max_workers=10,
        max_pages=3,  # Limit for testing
        verbose=True
    )

    results = scraper.scrape(url, field_schema)

    print(f"\n\nTotal results: {len(results)}")

    # Print first few results
    print("\nFirst 3 results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n--- Result {i} ---")
        print(json.dumps(result, indent=2))

    # Save results
    output_file = "stanford_engineering_profiles.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to {output_file}")

    scraper.close()
    return results


def example_berkeley_math():
    """Example: Scrape Berkeley Math graduate students."""
    print("\n" + "="*60)
    print("Example 2: Berkeley Math Graduate Students")
    print("="*60)

    url = "https://math.berkeley.edu/people/graduate-students"

    field_schema = {
        "name": "name of the student",
        "email": "their email address",
        "page_url": "url of their page",
        "research_area": "their research area or interests"
    }

    scraper = DirectoryScraper(
        use_llm=False,
        max_workers=5,
        verbose=True
    )

    results = scraper.scrape(url, field_schema)

    print(f"\n\nTotal results: {len(results)}")

    # Print first few results
    print("\nFirst 3 results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n--- Result {i} ---")
        print(json.dumps(result, indent=2))

    # Save results
    output_file = "berkeley_math_students.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to {output_file}")

    scraper.close()
    return results


def example_yc_companies():
    """Example: Scrape Y Combinator companies."""
    print("\n" + "="*60)
    print("Example 3: Y Combinator Companies")
    print("="*60)

    url = "https://www.ycombinator.com/companies/"

    field_schema = {
        "name": "company name",
        "description": "company description",
        "website": "company website url",
        "batch": "YC batch, e.g. S21, W22"
    }

    scraper = DirectoryScraper(
        use_llm=False,
        max_workers=5,
        max_pages=2,  # Limit for testing
        verbose=True
    )

    results = scraper.scrape(url, field_schema)

    print(f"\n\nTotal results: {len(results)}")

    # Print first few results
    print("\nFirst 3 results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n--- Result {i} ---")
        print(json.dumps(result, indent=2))

    # Save results
    output_file = "yc_companies.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to {output_file}")

    scraper.close()
    return results


def example_with_llm():
    """Example using LLM extraction."""
    print("\n" + "="*60)
    print("Example with LLM: Psychology Directory")
    print("="*60)

    url = "https://sdpsych.org/Find-a-Psychologist"

    field_schema = {
        "name": "psychologist name",
        "phone": "phone number",
        "email": "email address",
        "specialty": "area of specialty",
        "location": "office location or city"
    }

    scraper = DirectoryScraper(
        use_llm=True,  # Enable LLM
        llm_api_key=os.getenv("OPENAI_API_KEY"),
        max_workers=3,
        max_pages=2,
        verbose=True
    )

    results = scraper.scrape(url, field_schema)

    print(f"\n\nTotal results: {len(results)}")

    # Print first few results
    print("\nFirst 3 results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n--- Result {i} ---")
        print(json.dumps(result, indent=2))

    # Save results
    output_file = "psychologists.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\nResults saved to {output_file}")

    scraper.close()
    return results


if __name__ == "__main__":
    # Run examples
    # example_stanford_engineering()
    example_berkeley_math()
    # example_yc_companies()
    # example_with_llm()  # Requires OpenAI API key
