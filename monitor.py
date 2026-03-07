import os
import json
import feedparser
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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


def keyword_filter(title: str, snippet: str) -> bool:
    """Fast keyword-based pre-filter to reduce LLM calls."""
    text = f"{title} {snippet}".lower()
    
    # Positive signals - shipping resuming or becoming safe
    positive_keywords = [
        "resume", "resumed", "resuming", "resumes",
        "restored", "restore", "restoring",
        "safe passage", "safe transit",
        "reopened", "reopen", "reopening",
        "normal", "normaliz",
        "cleared", "clear for",
        "passage granted", "allowed through",
        "ships passing", "vessels passing",
        "transiting safely"
    ]
    
    # Must have at least one positive keyword to be worth LLM analysis
    has_positive = any(keyword in text for keyword in positive_keywords)
    return has_positive


def classify_with_llm(title: str, snippet: str) -> dict | None:
    """Use local Ollama model for classification."""
    import requests
    
    prompt = CLASSIFICATION_PROMPT.format(title=title, snippet=snippet)
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2:3b",  # Use your local 8b model
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for consistent output
                }
            },
            timeout=30
        )
        response.raise_for_status()
        result_text = response.json()["response"].strip()
        
        # Extract JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(result_text)
    except Exception as e:
        print(f"[LLM] Error calling Ollama: {e}")
        # Fallback to simple classification
        return {
            "relevant": True,  # If keyword matched, assume relevant
            "summary": "Potential shipping resumption (LLM unavailable)"
        }


def classify(title: str, snippet: str) -> dict | None:
    """Two-stage classification: keyword filter + LLM."""
    # Stage 1: Quick keyword filter
    if not keyword_filter(title, snippet):
        return {
            "relevant": False,
            "summary": "No positive keywords found"
        }
    
    # Stage 2: LLM classification for candidates
    print(f"[Classify] Keyword match - sending to LLM for analysis...")
    return classify_with_llm(title, snippet)


def send_telegram(message: str) -> None:
    """Send a message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        },
        timeout=15,
    )
    print(f"[Telegram] Status: {response.status_code}, Response: {response.json()}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def main() -> None:
    seen = load_seen()
    items = fetch_feed()
    print(f"[RSS] Fetched {len(items)} items, {len(seen)} already seen")

    sent_count = 0
    for item in items:
        link = item["link"]

        # Deduplicate
        if link in seen:
            continue
        seen.add(link)

        print(f"[New] {item['title'][:80]}...")

        # Classify article
        try:
            result = classify(item["title"], item["snippet"])
            print(f"[Classify] relevant={result.get('relevant')}, summary={result.get('summary', 'N/A')[:50]}...")
        except Exception as e:
            print(f"[Classify] Error: {e}")
            continue

        # Only send if relevant
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
            sent_count += 1
        except Exception as e:
            print(f"[Telegram] Error: {e}")
            continue

    save_seen(seen)
    print(f"[Done] {len(seen)} total seen articles, {sent_count} alerts sent")


if __name__ == "__main__":
    main()
