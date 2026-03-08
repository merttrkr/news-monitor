import os
import json
import time
import feedparser
import requests
from dotenv import load_dotenv

from config.rss_config import RSS_URL
from config.llm_config import (
    GROQ_API_URL,
    GROQ_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    CLASSIFICATION_PROMPT,
    CONFIDENCE_THRESHOLD,
    RATE_LIMIT_DELAY,
)
from config.keywords import POSITIVE_KEYWORDS
from config.message_templates import TELEGRAM_MESSAGE, LLM_FALLBACK_SUMMARY

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GIST_ID = os.environ.get("GIST_ID", "")

if not all([GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GH_TOKEN, GIST_ID]):
    raise SystemExit(
        "Missing required environment variables. "
        "Set GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GH_TOKEN, and GIST_ID "
        "in a .env file or your environment."
    )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


SEEN_TTL_SECONDS = 48 * 3600  # Prune entries older than 48 hours
GIST_FILENAME = "seen_articles.json"


def load_seen() -> dict:
    """Load previously seen article URLs with timestamps from GitHub Gist."""
    try:
        response = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={
                "Authorization": f"token {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=15
        )
        response.raise_for_status()
        
        gist_data = response.json()
        if GIST_FILENAME not in gist_data.get("files", {}):
            print(f"[Gist] File '{GIST_FILENAME}' not found in Gist, starting fresh")
            data = {}
        else:
            content = gist_data["files"][GIST_FILENAME]["content"]
            data = json.loads(content)
    except Exception as e:
        print(f"[Gist] Error loading from Gist: {e}, starting fresh")
        data = {}

    # Migrate from old flat-list format if needed
    if isinstance(data, list):
        now = time.time()
        data = {url: now for url in data}

    # Prune entries older than TTL
    cutoff = time.time() - SEEN_TTL_SECONDS
    return {url: ts for url, ts in data.items() if ts > cutoff}


def save_seen(seen: dict) -> None:
    """Persist seen article URLs with timestamps to GitHub Gist."""
    try:
        response = requests.patch(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={
                "Authorization": f"token {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            },
            json={
                "files": {
                    GIST_FILENAME: {
                        "content": json.dumps(seen, indent=2)
                    }
                }
            },
            timeout=15
        )
        response.raise_for_status()
        print(f"[Gist] Successfully saved {len(seen)} entries to Gist")
    except Exception as e:
        print(f"[Gist] Error saving to Gist: {e}")


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
    
    has_positive = any(keyword in text for keyword in POSITIVE_KEYWORDS)
    return has_positive


def _sanitize_input(text: str, max_length: int = 500) -> str:
    """Truncate and strip control characters from external input before LLM use."""
    sanitized = "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\t"))
    return sanitized[:max_length]


def classify_with_llm(title: str, snippet: str) -> dict:
    """Use Groq API with LLaMA model for classification."""
    import requests
    
    safe_title = _sanitize_input(title, max_length=300)
    safe_snippet = _sanitize_input(snippet, max_length=500)
    prompt = CLASSIFICATION_PROMPT.format(title=safe_title, snippet=safe_snippet)
    
    max_retries = 3
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": LLM_TEMPERATURE,
                    "max_tokens": 200
                },
                timeout=LLM_TIMEOUT
            )
            response.raise_for_status()
            result_text = response.json()["choices"][0]["message"]["content"].strip()
            
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(result_text)
            conf = parsed.get("confidence")
            if not isinstance(conf, (int, float)):
                parsed["confidence"] = 0.0
            else:
                parsed["confidence"] = max(0.0, min(1.0, float(conf)))
            return parsed
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"[LLM] Rate limited. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[LLM] Rate limit exceeded after {max_retries} attempts")
            else:
                print(f"[LLM] HTTP Error calling Groq API: {e}")
            break
        except Exception as e:
            print(f"[LLM] Error calling Groq API: {e}")
            break
    
    # Fallback to simple classification
    return {
        "confidence": 0.6,  # If keyword matched, assume moderate confidence
        "summary": LLM_FALLBACK_SUMMARY
    }


def classify(title: str, snippet: str) -> dict:
    """Two-stage classification: keyword filter + LLM."""
    if not keyword_filter(title, snippet):
        return {
            "confidence": 0.0,
            "summary": "No positive keywords found"
        }
    
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
        seen[link] = time.time()

        print(f"[New] {item['title'][:80]}...")

        try:
            result = classify(item["title"], item["snippet"])
            confidence = result.get("confidence", 0.0)
            print(f"[Classify] confidence={confidence:.2f}, summary={result.get('summary', 'N/A')[:50]}...")
            
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            print(f"[Classify] Error: {e}")
            continue

        if not isinstance(result, dict) or confidence < CONFIDENCE_THRESHOLD:
            continue

        message = TELEGRAM_MESSAGE.format(
            title=item["title"],
            confidence=f"{confidence * 100:.0f}",  # Convert to percentage
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
