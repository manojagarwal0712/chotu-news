#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import time
import random
import urllib.parse
from typing import List, Optional

import requests
import feedparser
from transformers import pipeline, AutoTokenizer

# ----------------------------
# Summarizer setup
# ----------------------------
MODEL_NAME = "facebook/bart-large-cnn"
summarizer = pipeline("summarization", model=MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# ----------------------------
# HTTP config
# ----------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
}

GOOGLE_NEWS_BASE = (
    "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
)

# ----------------------------
# Utilities
# ----------------------------
URL_RE = re.compile(r"^https?://", re.I)
TAG_RE = re.compile(r"<[^>]+>")

def is_valid_url(s: str) -> bool:
    return bool(URL_RE.match(s))

def strip_html(s: str) -> str:
    return TAG_RE.sub("", s or "").replace("&nbsp;", " ").strip()

def read_feeds_file(path: str = "feeds.txt") -> List[str]:
    """
    Read feeds.txt, remove inline comments and whitespace.
    Only return clean, valid URLs.
    """
    feeds: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            # remove inline comments
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if is_valid_url(line):
                feeds.append(line.strip())
            else:
                print(f"⚠ Skipping invalid feed line: {raw.rstrip()}")
    return feeds

def domain_from_url(url: str) -> Optional[str]:
    try:
        return urllib.parse.urlparse(url).netloc
    except Exception:
        return None

def google_news_fallback(url: str) -> Optional[str]:
    """
    Build a Google News RSS fallback for the feed's domain.
    Example: site:business-standard.com
    """
    dom = domain_from_url(url)
    if not dom:
        return None
    q = urllib.parse.quote_plus(f"site:{dom}")
    return GOOGLE_NEWS_BASE.format(query=q)

def safe_requests_get(url: str, timeout: float = 12.0, max_retries: int = 2):
    """
    Requests GET with headers, small retry/backoff for transient 403/5xx.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as e:
            last_exc = e
            # random small backoff to avoid getting flagged
            time.sleep(0.3 + random.random() * 0.7)
    raise last_exc

def fetch_feed(url: str):
    """
    Multi-strategy feed fetch:
    1) requests + feedparser on body
    2) direct feedparser on URL
    3) Google News RSS fallback for the domain
    """
    # Try #1: requests body -> feedparser
    try:
        resp = safe_requests_get(url)
        feed = feedparser.parse(resp.content)
        if feed and feed.entries:
            return feed
        else:
            print("⚠ No entries via requests+feedparser, trying direct feedparser…")
    except Exception as e:
        print(f"❌ Error fetching {url} (requests path): {e}")

    # Try #2: direct feedparser on URL
    try:
        feed = feedparser.parse(url)
        if feed and feed.entries:
            return feed
        else:
            print("⚠ No entries via direct feedparser, trying Google News fallback…")
    except Exception as e:
        print(f"❌ Direct feedparser failed for {url}: {e}")

    # Try #3: Google News fallback for the domain
    gnews = google_news_fallback(url)
    if gnews:
        try:
            resp = safe_requests_get(gnews)
            feed = feedparser.parse(resp.content)
            if feed and feed.entries:
                print(f"🔁 Using Google News fallback for {domain_from_url(url)}")
                return feed
        except Exception as e:
            print(f"❌ Google News fallback failed for {url}: {e}")

    # Nothing worked
    return None

# ----------------------------
# Summarization (warning-proof)
# ----------------------------
def summarize_text(text: str) -> str:
    """
    Summarize text without triggering 'max_length > input_length' warnings.
    - Compute exact token length with the model tokenizer.
    - If input is very short, just return it.
    - Ensure max_length < input_length.
    """
    clean = strip_html(text)
    if not clean:
        return ""

    # If extremely short, don't summarize
    words = clean.split()
    if len(words) < 8:
        return clean

    # Get exact token length
    try:
        inputs = tokenizer(clean, return_tensors="pt", truncation=True)
        input_len = int(inputs["input_ids"].shape[1])
    except Exception:
        # If tokenization fails, fall back to word-length heuristics
        input_len = max(1, int(len(words) * 1.3))

    # If still very small, return as-is
    if input_len <= 12:
        return clean

    # Choose safe lengths: target ~50% of input tokens, bounded
    max_len = min(130, max(20, input_len // 2))
    # absolutely ensure max_len < input_len
    if max_len >= input_len:
        max_len = max(8, input_len - 2)

    # min length ~40–60% of max_len, bounded
    min_len = max(5, min(max_len - 5, max_len // 2))

    try:
        out = summarizer(
            clean,
            max_length=max_len,
            min_length=min_len,
            do_sample=False,
        )
        return out[0]["summary_text"].strip()
    except Exception as e:
        # If BART is cranky on some inputs, fall back to a trimmed first sentence
        print(f"⚠ Summarization failed, returning trimmed text: {e}")
        # crude sentence cut
        first = re.split(r"(?<=[.!?])\s+", clean.strip())
        return first[0][:300].strip()

# ----------------------------
# Processing
# ----------------------------
def summarize_entry(entry) -> Optional[str]:
    """
    Build a reasonable input to summarize from an RSS entry.
    Prefer: content > summary > description > title
    """
    title = strip_html(entry.get("title", ""))
    body = ""
    # Many feeds store payload in different places
    if entry.get("content"):
        try:
            body = " ".join(strip_html(c.get("value", "")) for c in entry.get("content", []))
        except Exception:
            body = strip_html(entry.get("content", [{}])[0].get("value", ""))
    if not body:
        body = strip_html(entry.get("summary", "") or entry.get("description", ""))

    text = (title + ". " + body).strip() if title and body else (body or title)
    if not text:
        return None
    return summarize_text(text)

def process_feed(url: str, limit: int = 5):
    print(f"\n🔗 Processing feed: {url}")
    feed = fetch_feed(url)

    if not feed or not feed.entries:
        print("⚠ No entries found (after all fallbacks).")
        return

    for entry in feed.entries[:limit]:
        title = strip_html(entry.get("title", "No title"))
        link = entry.get("link", "")
        print(f"\n📰 {title}")
        try:
            summary = summarize_entry(entry)
            if summary:
                print(f"✍ {summary}")
            else:
                print("⚠ No content to summarize.")
        except Exception as e:
            print(f"❌ Entry summarization error: {e}")
        if link:
            print(f"🔗 {link}")

# ----------------------------
# Main
# ----------------------------
def main():
    feeds = read_feeds_file("feeds.txt")
    if not feeds:
        print("⚠ feeds.txt is empty or invalid.")
        return
    for url in feeds:
        process_feed(url, limit=3)

if __name__ == "__main__":
    main()
