# Configuration Files

This directory contains all configuration settings for the Hormuz Monitor application, organized by functional area.

## Files

### `rss_config.py`
RSS feed configuration for Google News searches.
- `RSS_URL`: The Google News RSS feed URL with search parameters for Strait of Hormuz news

### `llm_config.py`
LLM (Large Language Model) configuration for article classification.
- `GROQ_API_URL`: Groq API endpoint
- `GROQ_MODEL`: Model name to use for classification
- `LLM_TEMPERATURE`: Temperature setting for LLM responses
- `LLM_TIMEOUT`: API request timeout in seconds
- `CLASSIFICATION_PROMPT`: Template for the classification prompt
- `CONFIDENCE_THRESHOLD`: Minimum confidence to trigger an alert
- `RATE_LIMIT_DELAY`: Delay between API calls to avoid rate limits

### `keywords.py`
Keyword filters for pre-screening articles before LLM analysis.
- `POSITIVE_KEYWORDS`: List of keywords indicating shipping resumption or safety

### `message_templates.py`
Message templates for notifications.
- `TELEGRAM_MESSAGE`: Template for Telegram alert messages
- `LLM_FALLBACK_SUMMARY`: Fallback message when LLM is unavailable

## Usage

All configurations are imported in `monitor.py`:

```python
from config.rss_config import RSS_URL
from config.llm_config import GROQ_API_URL, GROQ_MODEL, ...
from config.keywords import POSITIVE_KEYWORDS
from config.message_templates import TELEGRAM_MESSAGE, LLM_FALLBACK_SUMMARY
```

## Customization

You can modify any of these files to customize the behavior of the monitor without touching the main application code.
