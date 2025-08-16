import feedparser
from bs4 import BeautifulSoup
import re
from datetime import datetime

def clean_html(raw_html):
    """Remove HTML tags and extra spaces from feed description."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(" ", strip=True)

def extract_details_link(entry):
    """Try to find a 'Details here' link from entry description if present."""
    if hasattr(entry, "description") and entry.description:
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

    source = "source"
    if link:
        try:
            source = re.sub(r"^https?://(www\.)?", "", link.split("/")[2])
        except Exception:
            pass

    details_link = extract_details_link(entry)

    if details_link:
        return f"{title} ([Details here]({details_link}), via [{source}]({link}))"
    else:
        return f"{title} (via [{source}]({link}))"

def fetch_and_summarize(feeds, limit=7):
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
    """Load RSS feeds from a file, stripping whitespace, tabs, and inline comments."""
    feeds = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if line:
                feeds.append(line)
    return feeds

if __name__ == "__main__":
    feeds = load_feeds("feeds.txt")
    lines = fetch_and_summarize(feeds, limit=7)

    summary_md = "## India One-Liner News\n\n"
    for line in lines:
        summary_md += f"- {line}\n"

    output_path = "docs/index.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary_md)

    print(f"✅ Saved {len(lines)} summaries to {output_path} at {datetime.now().isoformat()}")
