"""Message templates for notifications."""

TELEGRAM_MESSAGE = """\
🚢 Strait of Hormuz Shipping Update

Confidence: {confidence}%

Headline:
{title}

Summary:
{summary}

Source:
{link}

Time:
{published}
"""

# Fallback message when LLM is unavailable
LLM_FALLBACK_SUMMARY = "(LLM unavailable)"
