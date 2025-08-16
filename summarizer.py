import feedparser
import requests
from transformers import pipeline

# Initialize HuggingFace summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Strong browser-like headers to bypass 403 blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}


def fetch_feed(url):
    """Fetch RSS/Atom feed content safely with browser headers."""
    try:
        # Try fetching with requests first
        resp = requests.get(url.strip(), headers=HEADERS, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        return feed
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        # Fallback to direct feedparser
        try:
            feed = feedparser.parse(url.strip())
            return feed
        except Exception as e2:
            print(f"❌ Fallback failed for {url}: {e2}")
            return None


def summarize_text(text, max_length=40, min_length=10):
    """Summarize a given text safely."""
    try:
        return summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )[0]["summary_text"]
    except Exception as e:
        print(f"⚠ Summarization failed: {e}")
        return text


def process_feed(url):
    """Process a single feed URL."""
    print(f"🔗 Processing feed: {url}")
    feed = fetch_feed(url)

    if not feed or not feed.entries:
        print("⚠ No entries found.")
        return

    for entry in feed.entries[:3]:  # limit per feed
        title = entry.get("title", "No title")
        summary_input = entry.get("summary", entry.get("description", title))

        print(f"📰 {title}")
        short_summary = summarize_text(summary_input, max_length=30, min_length=5)
        print(f"✍ {short_summary}\n")


def main():
    with open("feeds.txt") as f:
        urls = [line.strip().split("#")[0].strip() for line in f if line.strip()]

    for url in urls:
        process_feed(url)


if __name__ == "__main__":
    main()
