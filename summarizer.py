import os
import sys
import time
import feedparser
import requests
from transformers import pipeline
from datetime import datetime
import subprocess

# ---------- CONFIG ----------
FEEDS_FILE = "feeds.txt"
OUTPUT_FILE = "README.md"
MAX_SUMMARY_LEN = 30   # max words for summary
MIN_SUMMARY_LEN = 5    # at least this many words
RETRIES = 3
BACKOFF = 2

# Init summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# ---------- HELPERS ----------
def fetch_feed(url):
    """Fetch RSS feed with retries and handle errors."""
    for i in range(RETRIES):
        try:
            print(f"🔗 Processing feed: {url}")
            feed = feedparser.parse(url)
            if feed.bozo:
                raise Exception(feed.bozo_exception)

            if feed.entries:
                return feed.entries
            else:
                raise Exception("No entries found")
        except Exception as e:
            wait = BACKOFF * (i + 1)
            print(f"⚠ Error fetching {url}: {e}, retrying in {wait}s")
            time.sleep(wait)

    print(f"❌ Failed after {RETRIES} retries: {url}")
    return []

def google_news_fallback(url):
    """Fallback: search site in Google News RSS."""
    try:
        print(f"⚠ No entries found in {url}, trying Google News fallback…")
        domain = url.split("/")[2]
        gnews_url = f"https://news.google.com/rss/search?q=site:{domain}"
        feed = feedparser.parse(gnews_url)
        if feed.entries:
            return feed.entries
        print(f"⚠ Google News fallback also returned nothing for {url}")
        return []
    except Exception as e:
        print(f"⚠ Google News fallback failed: {e}")
        return []

def safe_summarize(text):
    """Summarize safely with dynamic max_length."""
    if not text or len(text.split()) < MIN_SUMMARY_LEN:
        return text

    input_len = len(text.split())
    max_len = min(MAX_SUMMARY_LEN, max(MIN_SUMMARY_LEN, input_len - 2))

    try:
        summary = summarizer(
            text,
            max_length=max_len,
            min_length=MIN_SUMMARY_LEN,
            do_sample=False
        )[0]['summary_text']
        return summary
    except Exception as e:
        print(f"⚠ Summarization failed: {e}")
        return text

def write_readme(all_entries):
    """Write summaries into README.md."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 📰 News Summaries\n\n")
        f.write(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

        for source, entries in all_entries.items():
            f.write(f"## {source}\n\n")
            if not entries:
                f.write("_No news available_\n\n")
                continue
            for e in entries[:5]:
                title = e.get("title", "No title")
                link = e.get("link", "#")
                desc = e.get("description", title)
                summary = safe_summarize(desc)
                f.write(f"- [{title}]({link}) — {summary}\n")
            f.write("\n")

def git_commit():
    """Commit only if there are changes."""
    try:
        subprocess.run(["git", "config", "--global", "user.email", "you@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)

        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not status.stdout.strip():
            print("✅ No changes to commit")
            return

        subprocess.run(["git", "add", OUTPUT_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Update news summaries"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("✅ Changes committed and pushed")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Git commit failed: {e}")

# ---------- MAIN ----------
def main():
    all_entries = {}
    if not os.path.exists(FEEDS_FILE):
        print(f"❌ {FEEDS_FILE} not found")
        sys.exit(1)

    with open(FEEDS_FILE, "r") as f:
        feeds = [line.strip() for line in f if line.strip()]

    for feed in feeds:
        entries = fetch_feed(feed)
        if not entries:
            entries = google_news_fallback(feed)
        all_entries[feed] = entries

    write_readme(all_entries)
    git_commit()

if __name__ == "__main__":
    main()
