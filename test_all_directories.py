"""Test scraper on all example directories from the specification."""

import json
import time
from scraper import DirectoryScraper


def test_directory(name, url, field_schema, max_pages=1):
    """Test scraping a single directory."""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")

    scraper = DirectoryScraper(
        use_llm=True,  # Set to True to enable LLM fallback
        max_workers=5,
        max_pages=max_pages,
        verbose=True
    )

    start_time = time.time()

    try:
        results = scraper.scrape(url, field_schema)
        elapsed = time.time() - start_time

        print(f"\n{'='*70}")
        print(f"✓ SUCCESS: {name}")
        print(f"{'='*70}")
        print(f"Results:  {len(results)} entries")
        print(f"Time:     {elapsed:.2f} seconds")
        print(f"Speed:    {len(results)/elapsed:.2f} entries/second")

        if results:
            print(f"\nSample entry:")
            print(json.dumps(results[0], indent=2))

        # Save results
        filename = f"{name.lower().replace(' ', '_')}_results.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {filename}")

        return True

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"✗ FAILED: {name}")
        print(f"{'='*70}")
        print(f"Error:    {e}")
        print(f"Time:     {elapsed:.2f} seconds")
        return False

    finally:
        scraper.close()


def main():
    """Test all example directories."""

    print("""
╔══════════════════════════════════════════════════════════════════╗
║      GENERALIZED DIRECTORY SCRAPER - COMPREHENSIVE TEST          ║
╚══════════════════════════════════════════════════════════════════╝

Testing scraper on 7 different directory formats...
    """)

    test_cases = [
        {
            "name": "Berkeley Math Students",
            "url": "https://math.berkeley.edu/people/graduate-students",
            "schema": {
                "name": "name of the student",
                "email": "email address",
                "page_url": "profile page URL"
            },
            "max_pages": 1
        },
        {
            "name": "Stanford Engineering",
            "url": "https://profiles.stanford.edu/browse/school-of-engineering?p=1&ps=100",
            "schema": {
                "name": "name of the person",
                "email": "email address",
                "page_url": "profile page URL",
                "bio": "biography or research interests"
            },
            "max_pages": 2
        },
        {
            "name": "San Diego Psychologists",
            "url": "https://sdpsych.org/Find-a-Psychologist",
            "schema": {
                "name": "psychologist name",
                "phone": "phone number",
                "email": "email address",
                "specialty": "area of specialty",
                "location": "office location"
            },
            "max_pages": 1
        },
        {
            "name": "Houston Psychology",
            "url": "https://psychologyhouston.org/directory.php",
            "schema": {
                "name": "psychologist name",
                "phone": "phone number",
                "email": "email address",
                "website": "website URL"
            },
            "max_pages": 1
        },
        {
            "name": "Y Combinator Companies",
            "url": "https://www.ycombinator.com/companies/",
            "schema": {
                "name": "company name",
                "description": "company description",
                "website": "company website",
                "batch": "YC batch (e.g., S21, W22)"
            },
            "max_pages": 1
        },
        {
            "name": "Pennsylvania Health Services",
            "url": "https://sais.health.pa.gov/commonpoc/content/publicweb/nhinformation2.asp?COUNTY=Allegheny",
            "schema": {
                "name": "facility name",
                "address": "facility address",
                "phone": "phone number",
                "type": "facility type"
            },
            "max_pages": 1
        },
        {
            "name": "Bay Area Psychology",
            "url": "https://community.bapapsych.org/search/newsearch.asp?bst=&cdlGroupID=&txt_country=&txt_statelist=&txt_state=&ERR_LS_20250827_222102_27698=txt_state%7CLocation%7C20%7C0%7C%7C0",
            "schema": {
                "name": "psychologist name",
                "phone": "phone number",
                "email": "email address",
                "specialty": "specialty area"
            },
            "max_pages": 1
        }
    ]

    results_summary = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n[{i}/{len(test_cases)}] Starting test...")

        success = test_directory(
            name=test_case["name"],
            url=test_case["url"],
            field_schema=test_case["schema"],
            max_pages=test_case["max_pages"]
        )

        results_summary.append({
            "name": test_case["name"],
            "url": test_case["url"],
            "success": success
        })

        # Be nice to servers - wait between tests
        if i < len(test_cases):
            print("\n\nWaiting 3 seconds before next test...")
            time.sleep(3)

    # Print summary
    print("\n\n")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                      TEST SUMMARY                                ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    successful = sum(1 for r in results_summary if r["success"])
    total = len(results_summary)

    print(f"\nTotal Tests:     {total}")
    print(f"Successful:      {successful}")
    print(f"Failed:          {total - successful}")
    print(f"Success Rate:    {successful/total*100:.1f}%")

    print("\n\nDetailed Results:")
    print("-" * 70)
    for r in results_summary:
        status = "✓ PASS" if r["success"] else "✗ FAIL"
        print(f"{status}  {r['name']}")

    print("\n\n" + "="*70)
    if successful == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {total - successful} test(s) failed. Check errors above.")
    print("="*70)


if __name__ == "__main__":
    main()
