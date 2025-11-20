# Generalized Directory Scraper

A web scraper that extracts structured data from any directory website. Handles static/dynamic content, pagination, and various layouts without site-specific customization.

---

## 🚀 Get Started

### 1. Install

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install browser for JavaScript sites (optional but recommended)
playwright install chromium
```

### 2. Run a Test

```bash
# Quick test on Berkeley Math directory
python test_scraper.py
```

### 3. Try Your Own Directory

```python
from scraper import DirectoryScraper

# Define what fields you want
fields = {
    "name": "person's name",
    "email": "email address",
    "title": "job title or position"
}

# Scrape!
scraper = DirectoryScraper(verbose=True)
results = scraper.scrape("https://your-directory.com", fields)

print(f"Found {len(results)} entries!")
scraper.close()
```

---

## 📋 Running the Files

### Quick Test (Recommended Start Here)
```bash
python test_scraper.py
```
Tests scraping on Berkeley Math graduate students directory. Takes ~2 seconds.

### All Example Directories
```bash
python test_all_directories.py
```
Tests scraper on all 7 example directories from the specification. Takes ~2 minutes.

### Example Scripts
```bash
python examples/example_usage.py
```
Shows usage examples for different directory types. Edit the file to uncomment examples.

### Sixtyfour Enrichment (After Scraping)
```bash
# First scrape and save results
python examples/example_usage.py  # Saves to .json file

# Then enrich (requires Sixtyfour API key)
python sixtyfour_integration.py stanford
```

---

## 💡 How It Works

```
1. Fetch page (static or JavaScript-rendered)
   ↓
2. Detect structure (listings, pagination, detail pages)
   ↓
3. Extract data (DOM parsing + optional LLM fallback)
   ↓
4. Return structured results
```

**Key Features:**
- **Smart fetching**: Auto-detects if JavaScript is needed
- **Pattern detection**: Finds repeating elements automatically
- **Concurrent processing**: Scrapes multiple pages in parallel
- **Field-specific extraction**: Optimized for emails, phones, URLs, names, bios
- **LLM fallback**: Uses GPT-4o-mini when DOM parsing misses data

---

## 📖 Usage Examples

### Basic Scraping

```python
from scraper import DirectoryScraper

scraper = DirectoryScraper(
    max_workers=10,      # Concurrent workers (5-10 recommended)
    max_pages=100,       # Max pages to scrape
    verbose=True         # Show progress
)

results = scraper.scrape(
    url="https://math.berkeley.edu/people/graduate-students",
    field_schema={
        "name": "student name",
        "email": "email address"
    }
)

scraper.close()
```

### Save Results

```python
import json

with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### With LLM Enhancement (Optional)

```python
import os

scraper = DirectoryScraper(
    use_llm=True,
    llm_api_key=os.getenv("OPENAI_API_KEY"),  # Requires OpenAI API key
    max_workers=5
)

results = scraper.scrape(url, field_schema)
```

### Convenience Function

```python
from scraper.main import scrape_directory

results = scrape_directory(
    url="https://example.com/directory",
    field_schema={"name": "person name", "email": "email"},
    max_workers=10
)
```

---

## ⚙️ Configuration

### Environment Variables (Optional)

```bash
# Copy template
cp .env.example .env

# Edit .env and add keys (only if using LLM or enrichment)
OPENAI_API_KEY=sk-...           # For LLM extraction (optional)
SIXTYFOUR_API_KEY=sf-...        # For enrichment (optional)
```

### Scraper Options

```python
DirectoryScraper(
    use_llm=False,          # Enable LLM extraction (requires API key)
    llm_api_key=None,       # OpenAI API key
    max_workers=5,          # Concurrent workers (5-10 recommended)
    timeout=30,             # Request timeout in seconds
    max_pages=100,          # Maximum pages to scrape
    verbose=True            # Show progress
)
```

### Fetch Strategies

```python
from scraper.fetcher import FetchStrategy

# Auto-detect (default - recommended)
scraper.scrape(url, fields, fetch_strategy=FetchStrategy.AUTO)

# Force static (faster, for simple HTML)
scraper.scrape(url, fields, fetch_strategy=FetchStrategy.STATIC)

# Force dynamic (for JavaScript-heavy sites)
scraper.scrape(url, fields, fetch_strategy=FetchStrategy.DYNAMIC)
```

---

## 🔧 Sixtyfour Integration

### Enrich Scraped Data

```python
from sixtyfour_integration import enrich_scraped_data

# Enrich 100 sample records
enrich_scraped_data(
    input_file="results.json",
    output_file="enriched.json",
    enrich_fields=["linkedin_url", "company", "research_interests"],
    sample_size=100
)
```

### Direct API Usage

```python
from sixtyfour_integration import SixtyfourClient

client = SixtyfourClient()  # Reads API key from .env

enriched = client.enrich_lead(
    lead_data={"name": "John Doe", "email": "john@example.com"},
    enrich_fields=["linkedin_url", "company"]
)
```

---

## 🧪 Tested Directories

✅ **Berkeley Math Students** - https://math.berkeley.edu/people/graduate-students
✅ **Stanford Engineering** - https://profiles.stanford.edu/browse/school-of-engineering
✅ **Y Combinator Companies** - https://www.ycombinator.com/companies/
✅ **Psychology Associations** - Various psychology directories
✅ **Health Services** - Pennsylvania health services directory

---

## 🐛 Troubleshooting

### No Results Returned
```python
# Try verbose mode to see what's happening
scraper = DirectoryScraper(verbose=True)

# Try dynamic fetching for JavaScript sites
from scraper.fetcher import FetchStrategy
results = scraper.scrape(url, fields, FetchStrategy.DYNAMIC)
```

### Missing Fields
```python
# Enable LLM extraction
scraper = DirectoryScraper(
    use_llm=True,
    llm_api_key="sk-..."
)
```

### Slow Performance
```python
# Reduce concurrent workers
scraper = DirectoryScraper(max_workers=3)

# Use static fetching only
results = scraper.scrape(url, fields, FetchStrategy.STATIC)

# Limit pages for testing
scraper = DirectoryScraper(max_pages=5)
```

### Playwright Errors
```bash
# Reinstall browsers
playwright install --force chromium

# Install system dependencies (Linux)
playwright install-deps
```

---

## 📁 Project Structure

```
directory-scraper/
├── scraper/                    # Core scraper package
│   ├── main.py                # Main orchestrator
│   ├── fetcher.py             # Content fetching (static/dynamic)
│   ├── analyzer.py            # Pattern detection & pagination
│   ├── extractor.py           # Data extraction
│   ├── llm_extractor.py       # LLM fallback
│   └── utils.py               # Helper functions
│
├── examples/
│   └── example_usage.py       # Usage examples
│
├── test_scraper.py            # Quick test script
├── test_all_directories.py   # Comprehensive test
├── sixtyfour_integration.py  # Sixtyfour API client
│
├── requirements.txt           # Dependencies
├── .env.example              # Environment template
├── README.md                 # This file
├── ARCHITECTURE.md           # Technical design docs
└── PROJECT_SUMMARY.md        # Complete overview
```
---
