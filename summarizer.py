import feedparser
import requests
import time
import random
import re
from transformers import pipeline

# HuggingFace summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Browser-like headers
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) "
        "Gecko/20100101 Firefox/129.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# GET with retries
def robust_request(url, retries=3, backoff_factor=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as e:
            if resp.status_code in (403, 404):
                # immediate fallback on forbidden/not found
                print(f"❌ Permanent error {resp.status_code} for {url}, skipping retries")
                return None
            wait = (backoff_factor ** attempt) + random.random()
            print(f"⚠ Error fetching {url}: {e}, retrying in {wait:.1f}s")
            time.sleep(wait)
        except Exception as e:
            wait = (backoff_factor ** attempt) + random.random()
            print(f"⚠ Error fetching {url}: {e}, retrying in {wait:.1f}s")
            time.sleep(wait)
    print(f"❌ Failed after {retries} retries: {url}")
    return None

# Smart summary lengths
def get_summary_lengths(input_len: int):
    if input_len < 8:
        return None, None
    max_len = min(input_len - 1, max(12, input_len // 2))
    min_len = max(8, min(max_len - 2, input_len // 3))
    return min_len, max_len

# Ensure clean sentences
def clean_sentence(text: str) -> str:
    # Cut at last full stop if dangling
    if "." in text and not text.strip().endswith("."):
        return text[: text.rfind(".") + 1]
    return text

# Summarization wrapper
def dynamic_summarize(text: str) -> str:
    if not text:
        return "No content"
    input_len = len(text.split())
    min_len, max_len = get_summary_lengths(input_len)
    if not min_len or not max_len:
        return text.strip()
    try:
        summary = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False
        )
        if not summary or "summary_text" not in summary[0]:
            return text[:200]
        return clean_sentence(summary[0]["summary_text"].strip())
    except Exception as e:
        print(f"⚠ Summarization failed: {e}")
        return clean_sentence(text[:200])

# Process feed with fallback
def process_feed(feed_url: str, limit: int = 5):
    print(f"\n🔗 Processing feed: {feed_url}")
    raw_xml = robust_request(feed_url)

    def parse_and_print(raw_data, source_name="Feed"):
        feed = feedparser.parse(raw_d_
