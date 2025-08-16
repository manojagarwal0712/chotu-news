import feedparser
import requests
import time
import random
from transformers import pipeline

# Summarizer model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Headers to avoid 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    )
}

# Retry logic with exponential backoff
def robust_request(url, retries=3):
    for i in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            wait = (2 ** i) + random.random()
            print(f"⚠ Error fetching {url}: {e}, retrying in {wait:.1f}s")
            time.sleep(wait)
    print(f"❌ Failed after {retries} retries: {url}")
    return None

# Dynamic summary length
def dynamic_summarize(text):
    input_len = len(text.split())
    max_len = max(10, input_len // 2)  # about half the input length
    min_len = max(5, input_len // 4)
    try:
        summary = summarizer(
            text, max_length=max_len, min_length=min_len, do_sample=False
        )
        return summary[0]['summary_text']
    except Exception as e:
        print(f"⚠ Summarization failed: {e}")
        return text[:200]  # fallback: first 200 chars

# Process feed
def process_feed(feed_url):
    print(f"🔗 Processing feed: {feed_url}")
    raw_xml = robust_request(feed_url)
    if raw_xml:
        feed = feedparser.parse(raw_xml)
        if feed.entries:
            for entry in feed.entries[:5]:  # limit for demo
                title = entry.get("title", "No title")
                summary_input = entry.get("summary", title)
                summary = dynamic_summarize(summary_input)
                print(f"📰 {title}\n   ➡ {summary}\n")
            return
        else:
            print(f"⚠ No entries found in {feed_url}, trying Google News fallback…")
    else:
        print(f"⚠ No response from {feed_url}, trying Google News fallback…")

    # Google News fallback
    gnews_url = f"https://news.google.com/rss/search?q={feed_url}"
    raw_xml = robust_request(gnews_url)
    if raw_xml:
        feed = feedparser.parse(raw_xml)
        if feed.entries:
            for entry in feed.entries[:3]:
                title = entry.get("title", "No title")
                summary_input = entry.get("summary", title)
                summary = dynamic_summarize(summary_input)
                print(f"📰 {title}\n   ➡ {summary}\n")
        else:
            print(f"❌ Still no entries for {feed_url}")
    else:
        print(f"❌ Google News fallback also failed for {feed_url}")

# Main runner
if __name__ == "__main__":
    with open("feeds.txt") as f:
        feeds = [line.strip() for line in f if line.strip()]
    for url in feeds:
        process_feed(url)
