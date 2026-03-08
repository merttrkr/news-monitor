# Hormuz Monitor

Automated monitoring for Strait of Hormuz news using RSS feeds, LLM-powered classification, and Telegram notifications.

## Quick Setup for Local Testing

### Prerequisites
- Python 3.8 or higher
- Groq API key ([Get one here](https://groq.com))
- Telegram bot token and chat ID ([Create a bot](https://core.telegram.org/bots/tutorial))
- GitHub personal access token with `gist` scope ([Create token](https://github.com/settings/tokens))
- GitHub Gist ID (create a new gist at [gist.github.com](https://gist.github.com) with a file named `seen_articles.json`)

### Fast Start

```bash
# 1. Clone and navigate to the project
cd hormuz-monitor

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your:
# - GROQ_API_KEY
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
# - GH_TOKEN
# - GIST_ID

# 5. Run the monitor
python monitor.py
```

### Testing Environment Variables

Before running, ensure your `.env` file contains:

```env
GROQ_API_KEY=your_groq_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
GH_TOKEN=your_github_personal_access_token_here
GIST_ID=your_gist_id_here
```

### Test Run

To verify everything works:

```bash
# Activate virtual environment
source venv/bin/activate

# Run monitor (will check RSS feed once and exit)
python monitor.py

# Check for any error messages
# Successful run will process articles and send Telegram notifications if matches are found
```

## Configuration Files

All configuration settings are located in the `config/` directory, organized by functional area.

### `config/rss_config.py`
RSS feed configuration for Google News searches.
- `RSS_URL`: The Google News RSS feed URL with search parameters for Strait of Hormuz news

### `config/llm_config.py`
LLM (Large Language Model) configuration for article classification.
- `GROQ_API_URL`: Groq API endpoint
- `GROQ_MODEL`: Model name to use for classification
- `LLM_TEMPERATURE`: Temperature setting for LLM responses
- `LLM_TIMEOUT`: API request timeout in seconds
- `CLASSIFICATION_PROMPT`: Template for the classification prompt
- `CONFIDENCE_THRESHOLD`: Minimum confidence to trigger an alert
- `RATE_LIMIT_DELAY`: Delay between API calls to avoid rate limits

### `config/keywords.py`
Keyword filters for pre-screening articles before LLM analysis.
- `POSITIVE_KEYWORDS`: List of keywords indicating shipping resumption or safety

### `config/message_templates.py`
Message templates for notifications.
- `TELEGRAM_MESSAGE`: Template for Telegram alert messages
- `LLM_FALLBACK_SUMMARY`: Fallback message when LLM is unavailable

## Customization

You can modify any of the config files to customize the behavior of the monitor without touching the main application code.

## Project Structure

```
hormuz-monitor/
└── config/               # Configuration files
    ├── rss_config.py
    ├── llm_config.py
    ├── keywords.py
    └── message_templates.py
```

## Storage

The monitor uses a GitHub Gist to track previously seen articles, preventing duplicate notifications. The Gist stores article URLs with timestamps and automatically prunes entries older than 48 hours. ├── rss_config.py
    ├── llm_config.py
    ├── keywords.py
    └── message_templates.py
```
