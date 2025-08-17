import feedparser
import requests
import time
import random
from transformers import pipeline

# HuggingFace summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Stronger headers (NDTV/Gadgets360 block weak UA)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) "
        "Gecko/20100101 Firefox/129.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

# Retry logic with exponential backoff
def robust_request(url, retries=3, backoff_factor=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            wait = (backoff_factor ** attempt) + random.random()
            print(f"⚠ Error fetching {url}: {e}, retrying in {wait:.1f}s")
            time.sleep(wait)
    print(f"❌ Failed after {retries} retries: {url}")
    return None

# Safe summarization
def dynamic_summarize(text: str) -> str:
    if not text:
        return "No content"
    input_len = len(text.split())
    if input_len < 8:
        return text.strip()  # too short, return as-is

    max_len = max(15, min(100, input_len // 2))
    min_len = max(8, min(max_len - 2, input_len // 4))

    try:
        summary = summarizer(
            text, max_length=max_len, min_length=min_len, do_sample=False
        )
        if not summary or "summary_text" not in summary[0]:
            return text[:200]  # fallback
        return summary[0]["summary_text"].strip()
    except Exception as e:
        print(f"⚠ Summarization failed: {e}")
        return text[:200]

# Process feed or fallback
def process_feed(feed_url: str, limit: int = 5):
    print(f"\n🔗 Processing feed: {feed_url}")
    raw_xml = robust_request(feed_url)

    def parse_and_print(raw_data, source_name="Feed"):
        feed = feedparser.parse(raw_data)
        if feed.entries:
            for entry in feed.entries[:limit]:
                title = entry.get("title", "No title")
                summary_input = entry.get("summary", entry.get("description", title))
                summary = dynamic_summarize(summary_input)
                print(f"📰 {title}\n   ➡ {summary}\n")
            return True
        return False

    if raw_xml and parse_and_print(raw_xml):
        return

    print(f"⚠ No entries found in {feed_url}, trying Google News fallback…")
    # Use site-specific fallback (more reliable than last path part)
    domain = feed_url.split("/")[2]  # e.g. gadgets360.com
    gnews_url = f"https://news.google.com/rss/search?q=site:{domain}"

    raw_xml = robust_request(gnews_url)
    if raw_xml and parse_and_print(raw_xml, "Google News"):
        return
    print(f"❌ Still no entries for {feed_url}")

# Runner
if __name__ == "__main__":
    with open("feeds.txt") as f:
        feeds = [line.strip() for line in f if line.strip()]
    for url in feeds:
        process_feed(url)
