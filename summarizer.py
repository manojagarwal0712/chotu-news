import feedparser
from transformers import pipeline
import re

# ----------------------------
# Setup summarizer
# ----------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

def auto_summarize(text: str) -> str:
    """
    Summarize text with auto-adjusted max_length.
    Ensures shorter output than input and avoids warnings.
    """
    if not text or len(text.split()) < 5:
        return text.strip()

    input_len = len(text.split())

    # Output should be ~40-50% of input, but at least 20 words
    max_len = max(20, int(input_len * 0.5))
    min_len = max(10, int(max_len * 0.3))

    summary = summarizer(
        text,
        max_length=max_len,
        min_length=min_len,
        do_sample=False
    )[0]['summary_text']

    return summary.strip()


# ----------------------------
# Helpers
# ----------------------------
def is_valid_url(url: str) -> bool:
    """Validate if a string is a proper http/https URL."""
    return re.match(r'^https?://', url) is not None


def clean_feed_list(feed_file="feeds.txt"):
    """Read and clean feed URLs from file."""
    feeds = []
    with open(feed_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if is_valid_url(line):
                feeds.append(line)
            else:
                print(f"⚠ Skipping invalid URL: {line}")
    return feeds


def process_feed(feed_url: str):
    """Parse a single RSS feed and summarize entries."""
    try:
        feed = feedparser.parse(feed_url)
        print(f"\n🔗 Processing feed: {feed_url}")
        if not feed.entries:
            print("⚠ No entries found.")
            return

        for entry in feed.entries[:5]:  # limit per feed
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()
            content = entry.get("content", [{}])[0].get("value", "").strip()

            text = content or summary or title
            if not text:
                continue

            short_summary = auto_summarize(text)
            print(f"📰 {title}\n👉 {short_summary}\n")

    except Exception as e:
        print(f"❌ Error processing {feed_url}: {e}")


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    feeds = clean_feed_list("feeds.txt")
    for feed_url in feeds:
        process_feed(feed_url)
