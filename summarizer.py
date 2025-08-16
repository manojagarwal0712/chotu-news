import feedparser
import requests
from bs4 import BeautifulSoup
import re

def clean_html(raw_html):
    """Remove HTML tags and extra spaces from feed description."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(" ", strip=True)

def extract_details_link(entry):
    """Try to find a 'Details here' link from entry description if present."""
    if hasattr(entry, "description"):
        soup = BeautifulSoup(entry.description, "html.parser")
        a_tags = soup.find_all("a")
        for a in a_tags:
            if "detail" in a.get_text(strip=True).lower():
                return a.get("href")
    return None

def summarize_entry(entry):
    """Format a single RSS entry into one-liner news."""
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()
    source = re.sub(r"^https?://(www\.)?", "", link.split("/")[2]) if link else "source"

    # Try to find 'Details here' link inside description
    details_link = extract_details_link(entry)

    # Construct formatted output
    if details_link:
        return f"{title} ([Details here]({details_link}), via [{source}]({link}))"
    else:
        return f"{title} (via [{source}]({link}))"

def fetch_and_summarize(feeds, limit=10):
    """Fetch news from multiple feeds and return one-liners."""
    summaries = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                summaries.append(summarize_entry(entry))
        except Exception as e:
            summaries.append(f"⚠️ Error fetching {feed_url}: {e}")
    return summaries

def load_feeds(file_path="feeds.txt"):
    """Load RSS feeds from a file, stripping whitespace and ignoring comments."""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

if __name__ == "__main__":
    feeds = load_feeds("feeds.txt")
    lines = fetch_and_summarize(feeds, limit=7)

    print("## India One-Liner News\n")
    for line in lines:
        print(f"- {line}")
