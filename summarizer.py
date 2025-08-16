import feedparser
from requests_html import HTMLSession
from transformers import pipeline
import time

# -------------------------------
# Setup summarizer
# -------------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Setup HTML session
# -------------------------------
session = HTMLSession()

# -------------------------------
# Fetch article content
# -------------------------------
def fetch_article_content(url):
    try:
        r = session.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/139.0.0.0 Safari/537.36"
        })
        # Render JS for dynamic content
        r.html.render(timeout=15, sleep=2)

        # Extract paragraphs
        paragraphs = r.html.find("p")
        content = " ".join([p.text for p in paragraphs]).strip()

        # Fallback: meta description
        if not content:
            meta = r.html.find('meta[name="description"]', first=True)
            if meta and 'content' in meta.attrs:
                content = meta.attrs['content']

        if not content:
            print(f"⚠ No content found for {url}")
            return None

        return content
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None

# -------------------------------
# Summarize text
# -------------------------------
def summarize_text(text, max_len=130, min_len=30):
    if not text or len(text.split()) < 50:
        return None
    try:
        summary = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)
        return summary[0]["summary_text"]
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return None

# -------------------------------
# Categorization helper
# -------------------------------
def categorize_article(title, summary):
    text = (title + " " + (summary or "")).lower()
    if any(x in text for x in ["startup", "founder", "funding", "vc", "entrepreneur"]):
        return "Startups"
    if any(x in text for x in ["stock", "nifty", "sensex", "market", "share", "ipo"]):
        return "Markets"
    if any(x in text for x in ["ai", "tech", "software", "hardware", "gadget", "app"]):
        return "Tech"
    if any(x in text for x in ["election", "government", "policy", "minister", "parliament"]):
        return "Politics"
    return "General"

# -------------------------------
# Main fetch + summarize loop
# -------------------------------
def fetch_and_summarize(feeds):
    categorized = {"Startups": [], "Markets": [], "Tech": [], "Politics": [], "General": []}

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:  # Limit per feed
                title = entry.title
                link = entry.link

                content = fetch_article_content(link)
                if not content:
                    continue

                summary = summarize_text(content)
                if not summary:
                    continue

                category = categorize_article(title, summary)
                categorized[category].append({
                    "title": title,
                    "summary": summary,
                    "link": link
                })
        except Exception as e:
            print(f"❌ Failed to parse {feed_url}: {e}")

    return categorized

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    # Load feeds.txt
    feeds = []
    with open("feeds.txt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if line:
                feeds.append(line)

    categorized_articles = fetch_and_summarize(feeds)

    # Print results
    for cat, articles in categorized_articles.items():
        print(f"\n### {cat} ###")
        for art in articles:
            print(f"- {art['title']}\n  📝 {art['summary']}\n  🔗 {art['link']}")
