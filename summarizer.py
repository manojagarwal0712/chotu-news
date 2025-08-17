import os
import time
import requests
import feedparser
from datetime import datetime
from bs4 import BeautifulSoup

# ---------- CONFIG ----------
MAX_RETRIES = 3
RETRY_BACKOFF = 2
OUTPUT_FILE = "news.md"
FEEDS_FILE = "feeds.txt"
MAX_ITEMS = 5
# ----------------------------

def fetch_feed(url, retries=MAX_RETRIES):
    """Fetch RSS feed entries with retry logic and permanent error handling."""
    for attempt in range(1, retries + 1):
        try:
            print(f"🔗 Processing feed: {url}")
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            if not feed.entries:
                raise ValueError("No entries found")
            return feed.entries
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (403, 404):
                print(f"❌ Permanent error {e.response.status_code} for {url}, skipping retries")
                return []
            print(f"⚠ Error fetching {url}: {e}, retrying in {attempt * RETRY_BACKOFF}s")
            time.sleep(attempt * RETRY_BACKOFF)
        except Exception as e:
            print(f"⚠ Error fetching {url}: {e}, retrying in {attempt * RETRY_BACKOFF}s")
            time.sleep(attempt * RETRY_BACKOFF)
    print(f"❌ Failed after {retries} retries: {url}")
    return []

def google_news_fallback(query, max_items=MAX_ITEMS):
    """Fetch fallback results from Google News RSS search."""
    print(f"⚠ No entries found in {query}, trying Google News fallback…")
    fallback_url = f"https://news.google.com/rss/search?q={query}"
    try:
        feed = feedparser.parse(fallback_url)
        entries = []
        for entry in feed.entries[:max_items]:
            entries.append({
                "title": entry.title,
                "summary": BeautifulSoup(getattr(entry, "summary", ""), "html.parser").text,
                "link": entry.link
            })
        if not entries:
            print(f"⚠ Google News fallback also returned nothing for {query}")
        return entries
    except Exception as e:
        print(f"❌ Fallback failed for {query}: {e}")
        return []

def summarize_entry(entry):
    """Extract and clean title, summary, link."""
    title = getattr(entry, "title", "No title")
    summary = BeautifulSoup(getattr(entry, "summary", ""), "html.parser").text
    link = getattr(entry, "link", "")
    return {"title": title, "summary": summary, "link": link}

def process_feed(url):
    """Fetch feed or fallback and return summaries."""
    entries = fetch_feed(url)
    if not entries:  # fallback
        return google_news_fallback(url)
    return [summarize_entry(e) for e in entries[:MAX_ITEMS]]

def main():
    all_summaries = []

    with open(FEEDS_FILE, "r") as f:
        feeds = [line.strip() for line in f if line.strip()]

    for feed_url in feeds:
        summaries = process_feed(feed_url)
        if summaries:
            all_summaries.extend(summaries)

    if not all_summaries:
        print("⚠ No summaries to write, exiting.")
        return

    # Write summaries to file
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for s in all_summaries:
            f.write(f"📰 {s['title']}\n   ➡ {s['summary']}\n")
            if s["link"]:
                f.write(f"   🔗 {s['link']}\n\n")

    # Git commit & push
    os.system(f'git add {OUTPUT_FILE}')
    os.system('git commit -m "Add latest summaries" || echo "No changes to commit"')
    os.system('git push')

if __name__ == "__main__":
    main()
