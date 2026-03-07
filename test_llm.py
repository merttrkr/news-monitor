#!/usr/bin/env python3
"""Test script to verify LLM classification is working."""

import sys
import os

# Add current directory to path to import monitor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import classify

# Test article with positive keywords to trigger keyword filter
test_article = {
    "title": "Shipping Resumes Through Strait of Hormuz After Diplomatic Agreement",
    "snippet": "Commercial vessels have begun transiting safely through the Strait of Hormuz "
               "following a breakthrough diplomatic agreement between regional powers. "
               "Maritime authorities confirm normal shipping operations have resumed."
}

print("=" * 80)
print("TESTING LLM CLASSIFICATION")
print("=" * 80)
print(f"\nTest Article Title: {test_article['title']}")
print(f"Test Article Snippet: {test_article['snippet']}")
print("\n" + "=" * 80)
print("CLASSIFICATION RESULT")
print("=" * 80)

try:
    result = classify(test_article["title"], test_article["snippet"])
    print(f"\nRelevant: {result.get('relevant')}")
    print(f"Summary: {result.get('summary')}")
    print("\n" + "=" * 80)
    
    if result.get('relevant'):
        print("✅ SUCCESS - Article classified as relevant")
    else:
        print("⚠️  Article classified as NOT relevant")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
