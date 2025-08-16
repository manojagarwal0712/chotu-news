import feedparser
import requests
from transformers import pipeline

# Initialize summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Custom feed fetcher with User-Agent (fixes blocked feeds)
def fetch_feed(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url.strip(), headers=headers, timeout=10)
        resp.raise_for_status()
        return feedparser.parse(resp.text)
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None

# Summarize text with adaptive length
def summarize_text(text):
    input_length = len(text.split())
    if input_length < 5:
        return text  # Skip summarization for very short text

    # Dynamic max_length (half input size, but between 10–130)
    max_length = max(10, min(130, input_length // 2))

    try:
        summary = summarizer(
            text,
            max_length=max_length,
            min_length=5,
            do_sample=False
        )
        return summary[0]['summary_text']
    except Exception as e:
        return f"⚠ Error summarizing: {e}"

def process_feeds():
    with open("feeds.txt", "r") as f:
        feed_urls = f.readlines()

    for line in feed_urls:
        if not line.strip() or line.strip().startswith("#"):
            continue

        parts = line.strip().split("#")
        url = parts[0].strip()
        source = parts[1].strip() if len(parts) > 1 else "Unknown"

        print(f"\n🔗 Processing feed: {url} ({source})")
        feed = fetch_feed(url)

        if not feed or not feed.entries:
            print("⚠ No entries found.")
            continue

        for entry in feed.entries[:3]:  # Limit to 3 per feed
            title = entry.get("title", "No title")
            summary_input = entry.get("summary", entry.get("description", ""))

            print(f"\n📰 {title}")
            if summary_input:
                summary_output = summarize_text(summary_input)
                print(f"✍ Summary: {summary_output}")
            else:
                print("⚠ No content to summarize.")

if __name__ == "__main__":
    process_feeds()
