"""Quick test script for the directory scraper."""

import json
from scraper import DirectoryScraper


def test_berkeley_math():
    """Test scraping Berkeley Math graduate students."""
    print("\n" + "="*60)
    print("Testing: Berkeley Math Graduate Students")
    print("="*60)

    url = "https://math.berkeley.edu/people/graduate-students"

    field_schema = {
        "name": "name of the student",
        "email": "their email address",
        "page_url": "url of their page"
    }

    scraper = DirectoryScraper(
        use_llm=False,
        max_workers=3,
        max_pages=1,  # Just test one page
        verbose=True
    )

    try:
        results = scraper.scrape(url, field_schema)

        print(f"\n\nTotal results: {len(results)}")

        if results:
            print("\nFirst 3 results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n--- Result {i} ---")
                print(json.dumps(result, indent=2))

            # Save test results
            with open("test_results.json", 'w') as f:
                json.dump(results, f, indent=2)

            print(f"\nTest results saved to test_results.json")
            return True
        else:
            print("\nWARNING: No results extracted")
            return False

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        scraper.close()


if __name__ == "__main__":
    success = test_berkeley_math()
    if success:
        print("\n✓ Test passed!")
    else:
        print("\n✗ Test failed")
