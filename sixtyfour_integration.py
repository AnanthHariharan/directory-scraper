"""Integration with Sixtyfour API for lead enrichment."""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()


class SixtyfourClient:
    """Client for Sixtyfour API."""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize Sixtyfour client.

        Args:
            api_key: API key (defaults to env variable)
            api_url: API URL (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("SIXTYFOUR_API_KEY")
        self.api_url = api_url or os.getenv(
            "SIXTYFOUR_API_URL",
            "https://api.sixtyfour.ai/enrich-lead"
        )

        if not self.api_key:
            raise ValueError("SIXTYFOUR_API_KEY not provided")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def enrich_lead(
        self,
        lead_data: Dict[str, Any],
        enrich_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Enrich a single lead.

        Args:
            lead_data: Lead data to enrich
            enrich_fields: Specific fields to enrich (optional)

        Returns:
            Enriched lead data
        """
        payload = {
            "lead": lead_data
        }

        if enrich_fields:
            payload["enrich_fields"] = enrich_fields

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error enriching lead: {e}")
            return lead_data

    def enrich_leads_batch(
        self,
        leads: List[Dict[str, Any]],
        enrich_fields: Optional[List[str]] = None,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple leads in batches.

        Args:
            leads: List of lead data
            enrich_fields: Fields to enrich
            batch_size: Batch size

        Returns:
            List of enriched leads
        """
        enriched = []

        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]

            print(f"Enriching batch {i//batch_size + 1} ({len(batch)} leads)...")

            for lead in batch:
                enriched_lead = self.enrich_lead(lead, enrich_fields)
                enriched.append(enriched_lead)

        return enriched


def enrich_scraped_data(
    input_file: str,
    output_file: str,
    enrich_fields: Optional[List[str]] = None,
    sample_size: Optional[int] = 100
):
    """
    Enrich scraped data using Sixtyfour API.

    Args:
        input_file: Path to input JSON file with scraped data
        output_file: Path to output JSON file for enriched data
        enrich_fields: Fields to enrich
        sample_size: Number of records to enrich (None for all)
    """
    # Load scraped data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    # Sample if requested
    if sample_size and len(data) > sample_size:
        print(f"Sampling {sample_size} records from {len(data)} total...")
        import random
        data = random.sample(data, sample_size)

    print(f"Enriching {len(data)} records...")

    # Initialize client
    client = SixtyfourClient()

    # Enrich
    enriched_data = client.enrich_leads_batch(data, enrich_fields)

    # Save results
    print(f"Saving enriched data to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(enriched_data, f, indent=2)

    print(f"Done! Enriched {len(enriched_data)} records")

    # Print summary
    print("\n" + "="*60)
    print("Enrichment Summary")
    print("="*60)

    if enriched_data:
        sample = enriched_data[0]
        print("\nSample enriched record:")
        print(json.dumps(sample, indent=2))

        print("\nFields in enriched data:")
        for field in sample.keys():
            print(f"  - {field}")


def example_enrich_stanford_profiles():
    """Example: Enrich Stanford profiles."""

    print("\n" + "="*60)
    print("Enriching Stanford Engineering Profiles")
    print("="*60)

    # Fields to enrich
    enrich_fields = [
        "linkedin_url",
        "company",
        "job_title",
        "research_interests",
        "publications_count"
    ]

    enrich_scraped_data(
        input_file="stanford_engineering_profiles.json",
        output_file="stanford_engineering_enriched.json",
        enrich_fields=enrich_fields,
        sample_size=100
    )


def example_enrich_berkeley_students():
    """Example: Enrich Berkeley Math students."""

    print("\n" + "="*60)
    print("Enriching Berkeley Math Students")
    print("="*60)

    # Fields to enrich
    enrich_fields = [
        "linkedin_url",
        "advisor",
        "publications",
        "research_interests",
        "graduation_year"
    ]

    enrich_scraped_data(
        input_file="berkeley_math_students.json",
        output_file="berkeley_math_enriched.json",
        enrich_fields=enrich_fields,
        sample_size=100
    )


if __name__ == "__main__":
    # Run enrichment examples
    # Make sure you have scraped data first!

    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "stanford":
            example_enrich_stanford_profiles()
        elif sys.argv[1] == "berkeley":
            example_enrich_berkeley_students()
        else:
            print("Usage: python sixtyfour_integration.py [stanford|berkeley]")
    else:
        print("Usage: python sixtyfour_integration.py [stanford|berkeley]")
        print("\nOr use the functions directly in your code:")
        print("  from sixtyfour_integration import SixtyfourClient, enrich_scraped_data")
