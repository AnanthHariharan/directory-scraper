#!/usr/bin/env python3
"""Test scraper with LLM enhancement and compare to baseline."""

import os
import json
from scraper import DirectoryScraper
from dotenv import load_dotenv

load_dotenv()

# Test cases - focusing on ones that had high null rates
TEST_CASES = [
    {
        "name": "Berkeley Math (Table-based)",
        "url": "https://math.berkeley.edu/people/graduate-students",
        "fields": {
            "name": "student name",
            "email": "email address",
            "page_url": "personal website URL"
        },
        "max_pages": 1
    },
    {
        "name": "San Diego Psychologists (High failure rate)",
        "url": "https://sdpsych.org/Find-a-Psychologist",
        "fields": {
            "name": "psychologist name",
            "phone": "phone number",
            "email": "email address",
            "specialty": "specialty or focus area",
            "location": "city or location"
        },
        "max_pages": 1
    }
]

def calculate_null_percentage(results, field_names):
    """Calculate percentage of null/empty fields."""
    if not results:
        return 100.0

    total_fields = len(results) * len(field_names)
    null_count = 0

    for record in results:
        for field in field_names:
            value = record.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                null_count += 1

    return (null_count / total_fields * 100) if total_fields > 0 else 100.0

def run_comparison():
    """Run scraper with and without LLM and compare."""

    print("=" * 80)
    print("SCRAPER COMPARISON: WITH vs WITHOUT LLM")
    print("=" * 80)
    print()

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OPENAI_API_KEY found in .env file")
        return

    for test_case in TEST_CASES:
        print(f"\n{'─' * 80}")
        print(f"Test: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        print(f"{'─' * 80}\n")

        # Test WITHOUT LLM
        print("🔹 Running WITHOUT LLM...")
        scraper_no_llm = DirectoryScraper(
            use_llm=False,
            max_pages=test_case['max_pages'],
            verbose=False
        )

        try:
            results_no_llm = scraper_no_llm.scrape(
                test_case['url'],
                test_case['fields']
            )
            null_pct_no_llm = calculate_null_percentage(results_no_llm, list(test_case['fields'].keys()))

            print(f"   Records: {len(results_no_llm)}")
            print(f"   Null/Empty: {null_pct_no_llm:.1f}%")

            # Show sample
            if results_no_llm:
                print(f"   Sample: {json.dumps(results_no_llm[0], indent=2)}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results_no_llm = []
            null_pct_no_llm = 100.0

        finally:
            scraper_no_llm.close()

        print()

        # Test WITH LLM
        print("🔸 Running WITH LLM...")
        scraper_with_llm = DirectoryScraper(
            use_llm=True,
            llm_api_key=api_key,
            max_pages=test_case['max_pages'],
            verbose=False
        )

        try:
            results_with_llm = scraper_with_llm.scrape(
                test_case['url'],
                test_case['fields']
            )
            null_pct_with_llm = calculate_null_percentage(results_with_llm, list(test_case['fields'].keys()))

            print(f"   Records: {len(results_with_llm)}")
            print(f"   Null/Empty: {null_pct_with_llm:.1f}%")

            # Show sample
            if results_with_llm:
                print(f"   Sample: {json.dumps(results_with_llm[0], indent=2)}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            results_with_llm = []
            null_pct_with_llm = 100.0

        finally:
            scraper_with_llm.close()

        # Comparison
        print()
        print("📊 COMPARISON:")
        print(f"   Without LLM: {null_pct_no_llm:.1f}% null/empty")
        print(f"   With LLM:    {null_pct_with_llm:.1f}% null/empty")

        improvement = null_pct_no_llm - null_pct_with_llm
        if improvement > 0:
            print(f"   ✅ IMPROVEMENT: {improvement:.1f} percentage points better with LLM")
        elif improvement < 0:
            print(f"   ⚠️  REGRESSION: {abs(improvement):.1f} percentage points worse with LLM")
        else:
            print(f"   ➖ No change")

        # Save results
        output_file = f"{test_case['name'].lower().replace(' ', '_')}_llm_comparison.json"
        with open(output_file, 'w') as f:
            json.dump({
                'test_name': test_case['name'],
                'without_llm': {
                    'records': len(results_no_llm),
                    'null_percentage': null_pct_no_llm,
                    'sample': results_no_llm[:3] if results_no_llm else []
                },
                'with_llm': {
                    'records': len(results_with_llm),
                    'null_percentage': null_pct_with_llm,
                    'sample': results_with_llm[:3] if results_with_llm else []
                }
            }, f, indent=2)

        print(f"   💾 Results saved to: {output_file}")

    print(f"\n{'=' * 80}")
    print("COMPARISON COMPLETE")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    run_comparison()
