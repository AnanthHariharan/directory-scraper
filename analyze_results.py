#!/usr/bin/env python3
"""Analyze scraper results to calculate null/empty field percentages."""

import json
from pathlib import Path
from collections import defaultdict

def analyze_results():
    """Analyze all result JSON files and calculate null percentages."""

    result_files = [
        "berkeley_math_students_results.json",
        "stanford_engineering_results.json",
        "san_diego_psychologists_results.json",
        "houston_psychology_results.json",
        "y_combinator_companies_results.json",
        "pennsylvania_health_services_results.json",
        "bay_area_psychology_results.json"
    ]

    print("=" * 80)
    print("SCRAPER QUALITY ANALYSIS - NULL/EMPTY FIELD PERCENTAGES")
    print("=" * 80)
    print()

    total_stats = defaultdict(lambda: {"total": 0, "null": 0, "empty": 0})

    for filename in result_files:
        filepath = Path(filename)
        if not filepath.exists():
            continue

        with open(filepath, 'r') as f:
            data = json.load(f)

        if not data:
            print(f"⚠️  {filename}: No data")
            continue

        print(f"\n{'─' * 80}")
        print(f"📄 {filename}")
        print(f"{'─' * 80}")
        print(f"Total records: {len(data)}")
        print()

        # Calculate stats per field
        field_stats = defaultdict(lambda: {"total": 0, "null": 0, "empty": 0})

        for record in data:
            for field, value in record.items():
                field_stats[field]["total"] += 1
                total_stats[field]["total"] += 1

                if value is None:
                    field_stats[field]["null"] += 1
                    total_stats[field]["null"] += 1
                elif isinstance(value, str) and value.strip() == "":
                    field_stats[field]["empty"] += 1
                    total_stats[field]["empty"] += 1

        # Print field-by-field analysis
        print(f"{'Field':<20} {'Null %':>10} {'Empty %':>10} {'Missing %':>12} {'Total':>8}")
        print(f"{'-' * 20} {'-' * 10} {'-' * 10} {'-' * 12} {'-' * 8}")

        for field in sorted(field_stats.keys()):
            stats = field_stats[field]
            null_pct = (stats["null"] / stats["total"] * 100) if stats["total"] > 0 else 0
            empty_pct = (stats["empty"] / stats["total"] * 100) if stats["total"] > 0 else 0
            missing_pct = null_pct + empty_pct

            print(f"{field:<20} {null_pct:>9.1f}% {empty_pct:>9.1f}% {missing_pct:>11.1f}% {stats['total']:>8}")

    # Overall summary
    print(f"\n{'=' * 80}")
    print("OVERALL SUMMARY (across all datasets)")
    print(f"{'=' * 80}")
    print()
    print(f"{'Field':<20} {'Null %':>10} {'Empty %':>10} {'Missing %':>12} {'Total':>8}")
    print(f"{'-' * 20} {'-' * 10} {'-' * 10} {'-' * 12} {'-' * 8}")

    overall_null = 0
    overall_empty = 0
    overall_total = 0

    for field in sorted(total_stats.keys()):
        stats = total_stats[field]
        null_pct = (stats["null"] / stats["total"] * 100) if stats["total"] > 0 else 0
        empty_pct = (stats["empty"] / stats["total"] * 100) if stats["total"] > 0 else 0
        missing_pct = null_pct + empty_pct

        overall_null += stats["null"]
        overall_empty += stats["empty"]
        overall_total += stats["total"]

        print(f"{field:<20} {null_pct:>9.1f}% {empty_pct:>9.1f}% {missing_pct:>11.1f}% {stats['total']:>8}")

    print(f"{'-' * 20} {'-' * 10} {'-' * 10} {'-' * 12} {'-' * 8}")
    overall_null_pct = (overall_null / overall_total * 100) if overall_total > 0 else 0
    overall_empty_pct = (overall_empty / overall_total * 100) if overall_total > 0 else 0
    overall_missing_pct = overall_null_pct + overall_empty_pct

    print(f"{'TOTAL':<20} {overall_null_pct:>9.1f}% {overall_empty_pct:>9.1f}% {overall_missing_pct:>11.1f}% {overall_total:>8}")

    print(f"\n{'=' * 80}")
    print(f"🚨 CRITICAL FINDING: {overall_missing_pct:.1f}% of all fields are NULL or EMPTY")
    print(f"{'=' * 80}")

if __name__ == "__main__":
    analyze_results()
