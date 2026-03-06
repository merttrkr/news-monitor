import os
import json
import feedparser
import requests
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=%22Strait+of+Hormuz%22+"
    "%22shipping+resumes%22+OR+%22transit+resumes%22+OR+"
    "%22safe+passage%22+OR+%22shipping+restored%22+OR+"
    "%22normal+transit%22+OR+%22navigation+restored%22"
    "&hl=en-US&gl=US&ceid=US:en"
)

SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_articles.json")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

CLASSIFICATION_PROMPT = """\
You are a geopolitical news classifier.

Determine whether this article indicates that commercial shipping
through the Strait of Hormuz has resumed or become safe again.

Return ONLY valid JSON:

{{
 "relevant": true or false,
 "summary": "one short sentence explaining the signal"
}}

Article headline:
{title}

Snippet:
{snippet}

Rules
- Ignore speculation
- Ignore historical discussion
- Ignore unrelated naval activity
- Only mark relevant if the article strongly suggests shipping has resumed or become safe
"""

TELEGRAM_MSG = """\
🚢 Strait of Hormuz Shipping Update

Headline:
{title}

Summary:
{summary}

Source:
{link}

Time:
{published}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_seen() -> set:
    """Load previously seen article URLs."""
    try:
        with open(SEEN_PATH, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(seen: set) -> None:
    """Persist seen article URLs."""
    with open(SEEN_PATH, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def fetch_feed() -> list[dict]:
    """Fetch and parse the Google News RSS feed."""
    feed = feedparser.parse(RSS_URL)
    items = []
    for entry in feed.entries:
        items.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "snippet": entry.get("summary", ""),
                "published": entry.get("published", ""),
            }
        )
    return items


def classify(title: str, snippet: str) -> dict | None:
    """Ask Gemini whether the article signals shipping resumption."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = CLASSIFICATION_PROMPT.format(title=title, snippet=snippet)
    response = model.generate_content(prompt)

    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    return json.loads(text)


def send_telegram(message: str) -> None:
    """Send a message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        },
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    seen = load_seen()
    items = fetch_feed()

    for item in items:
        link = item["link"]

        # Deduplicate
        if link in seen:
            continue
        seen.add(link)

        # Classify via Gemini
        try:
            result = classify(item["title"], item["snippet"])
        except Exception:
            continue

        if not isinstance(result, dict) or not result.get("relevant"):
            continue

        # Send Telegram alert
        message = TELEGRAM_MSG.format(
            title=item["title"],
            summary=result.get("summary", "N/A"),
            link=item["link"],
            published=item["published"],
        )
        try:
            send_telegram(message)
        except Exception:
            continue

    save_seen(seen)


if __name__ == "__main__":
    main()
