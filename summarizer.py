import os
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from transformers import pipeline
from urllib.parse import quote
import subprocess

# -------------------------------
# Load HuggingFace Summarizer
# -------------------------------
print("🔧 Loading summarizer model…")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Feed list (RSS sources)
# -------------------------------
FEEDS = [
    "https://indianexpress.com/section/india/feed/",
    "https://indianexpress.com/section/technology/feed/",
    "https://www.livemint.com/rss/companies",
    "https://www.livemint.com/rss/markets",
    "https://www.livemint.com/rss/technology",
    "https://www.business-standard.com/rss/markets-106.rss",
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.gadgets360.com/rss/news",
    "https://inc42.com/feed/",
    "https://entrackr.com/feed/",
    "https://www.hindustantimes.com/rss/topnews/rssfeed.xml",
    "https://www.moneycontrol.com/rss/latestnews.xml",
    "https://www.moneycontrol.com/rss/technology.xml",
]

# -------------------------------
# Smart summarizer wrapper
# -------------------------------
def smart_summarize(text: str) -> str:
    """Summarize text with dynamic max_length."""
    if not text:
        return ""
    input_len = len(text.split())
    max_len = max(5, min(50, input_len - 2))  # ensure shorter than input
    try:
        summary = summarizer(text, max_length=max_len, min_length=5, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return text[:200]  # fallback: truncate

# -------------------------------
# Google News fallback fetch
# -------------------------------
async def fetch_google_news_fallback(session, topic="India news"):
    url = f"https://news.google.com/rss/search?q={quote(topic)}&hl=en-IN&gl=IN&ceid=IN:en"
    print(f"🔗 Fetching Google News fallback: {url}")
    try:
        async with session.get(url, timeout=15) as resp:
            resp.raise_for_status()
            text = await resp.text()
            parsed = feedparser.parse(text)
            return parsed.entries
    except Exception as e:
        print(f"❌ Google News fallback failed: {e}")
        return []

# -------------------------------
# Fetch and parse feed
# -------------------------------
async def fetch_feed(session, feed_url, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(feed_url, timeout=20) as resp:
                resp.raise_for_status()
                text = await resp.text()
                parsed = feedparser.parse(text)
                if parsed.entries:
                    return parsed.entries
                else:
                    raise ValueError("No entries in feed")
        except Exception as e:
            wait_time = 2 * (attempt + 1)
            print(f"⚠ Error fetching {feed_url}: {e}, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)
    print(f"❌ Failed after {retries} retries: {feed_url}")
    return []

# -------------------------------
# Process feed with fallback
# -------------------------------
async def process_feed(session, feed_url):
    print(f"🔗 Processing feed: {feed_url}")
    entries = await fetch_feed(session, feed_url)

    if not entries:
        print(f"⚠ No entries found in {feed_url}, trying Google News fallback…")
        topic = "technology" if "tech" in feed_url else "markets" if "market" in feed_url else "India news"
        entries = await fetch_google_news_fallback(session, topic)

    results = []
    for entry in entries[:5]:  # only top 5 from each feed
        title = entry.get("title", "No title")
        summary_text = smart_summarize(entry.get("summary", title))
        link = entry.get("link", "#")
        results.append(f"- {title}\n  {summary_text}\n  🔗 {link}\n")
    return results

# -------------------------------
# Main async runner
# -------------------------------
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [process_feed(session, url) for url in FEEDS]
        results = await asyncio.gather(*tasks)
        all_summaries = [item for sublist in results for item in sublist]

        output = "# 📰 Daily News Summaries\n\n"
        output += "\n".join(all_summaries)
        output += f"\n\n_Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_\n"

        with open("README.md", "w", encoding="utf-8") as f:
            f.write(output)

        # Git commit & push
        subprocess.run(["git", "add", "README.md"])
        subprocess.run(["git", "commit", "-m", "Update news summaries"])
        subprocess.run(["git", "push", "origin", "main"])
        print("✅ Changes committed and pushed")

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    asyncio.run(main())
