"""LLM-based data extractor for complex or unstructured content."""

import json
import os
from typing import Dict, Any, List, Optional

from bs4 import BeautifulSoup
import openai


class LLMExtractor:
    """Uses LLM to extract structured data from HTML."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize LLM extractor.

        Args:
            api_key: OpenAI API key (defaults to env variable)
            model: Model to use
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key) if self.api_key else None

    def extract_from_html(
        self,
        html: str,
        field_schema: Dict[str, str],
        max_length: int = 8000
    ) -> Dict[str, Any]:
        """
        Extract data from HTML using LLM.

        Args:
            html: HTML content
            field_schema: Field schema
            max_length: Maximum HTML length to process

        Returns:
            Extracted data
        """
        if not self.client:
            return {field: None for field in field_schema.keys()}

        # Clean and truncate HTML
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        # Get text representation
        text = soup.get_text(separator='\n', strip=True)

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        # Build prompt
        prompt = self._build_extraction_prompt(text, field_schema)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured data from the provided text and return it as valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return {field: None for field in field_schema.keys()}

    def extract_from_elements(
        self,
        elements: List[str],
        field_schema: Dict[str, str],
        batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract data from multiple HTML elements in batches.

        Args:
            elements: List of HTML strings
            field_schema: Field schema
            batch_size: Number of elements to process at once

        Returns:
            List of extracted data dictionaries
        """
        if not self.client:
            return [{field: None for field in field_schema.keys()} for _ in elements]

        results = []

        # Process in batches
        for i in range(0, len(elements), batch_size):
            batch = elements[i:i + batch_size]
            batch_results = self._extract_batch(batch, field_schema)
            results.extend(batch_results)

        return results

    def _extract_batch(
        self,
        elements: List[str],
        field_schema: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Extract data from a batch of elements."""

        # Clean elements
        cleaned = []
        for html in elements:
            soup = BeautifulSoup(html, 'lxml')
            for tag in soup(['script', 'style']):
                tag.decompose()
            text = soup.get_text(separator=' ', strip=True)
            cleaned.append(text[:1000])  # Limit each element

        # Build prompt
        prompt = self._build_batch_extraction_prompt(cleaned, field_schema)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured data from multiple entries and return as a JSON array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Handle different response formats
            if 'results' in result:
                return result['results']
            elif 'data' in result:
                return result['data']
            elif isinstance(result, list):
                return result
            else:
                return [result]

        except Exception as e:
            print(f"Batch LLM extraction failed: {e}")
            return [{field: None for field in field_schema.keys()} for _ in elements]

    def _build_extraction_prompt(
        self,
        text: str,
        field_schema: Dict[str, str]
    ) -> str:
        """Build prompt for single extraction."""

        schema_desc = json.dumps(field_schema, indent=2)

        prompt = f"""Extract the following fields from the text below:

Field Schema:
{schema_desc}

Text:
{text}

Return the extracted data as a JSON object with the field names as keys. If a field cannot be found, set its value to null.
"""
        return prompt

    def _build_batch_extraction_prompt(
        self,
        texts: List[str],
        field_schema: Dict[str, str]
    ) -> str:
        """Build prompt for batch extraction."""

        schema_desc = json.dumps(field_schema, indent=2)

        entries_text = ""
        for i, text in enumerate(texts, 1):
            entries_text += f"\n--- Entry {i} ---\n{text}\n"

        prompt = f"""Extract the following fields from each entry below:

Field Schema:
{schema_desc}

{entries_text}

Return the extracted data as a JSON object with a "results" key containing an array of objects, one for each entry.
If a field cannot be found in an entry, set its value to null.

Example format:
{{
  "results": [
    {{"field1": "value1", "field2": "value2"}},
    {{"field1": "value1", "field2": "value2"}}
  ]
}}
"""
        return prompt

    def smart_extract(
        self,
        html: str,
        field_schema: Dict[str, str],
        fallback_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Smart extraction that only uses LLM for missing fields.

        Args:
            html: HTML content
            field_schema: Field schema
            fallback_data: Data already extracted by other methods

        Returns:
            Complete extracted data
        """
        if not fallback_data:
            return self.extract_from_html(html, field_schema)

        # Find missing fields
        missing_fields = {
            k: v for k, v in field_schema.items()
            if not fallback_data.get(k)
        }

        if not missing_fields:
            return fallback_data

        # Extract only missing fields
        llm_data = self.extract_from_html(html, missing_fields)

        # Merge results
        result = {**fallback_data}
        for field, value in llm_data.items():
            if value and not result.get(field):
                result[field] = value

        return result
