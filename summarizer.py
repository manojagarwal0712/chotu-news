import feedparser
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

# -------------------------------
# Setup summarizer
# -------------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Fetch and summarize single article
# -------------------------------
def fetch_article_content(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Prefer <p> tags for article text
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        content = " ".join(paragraphs)
        return content.strip()
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return ""

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
    text = (title + " " + summary).lower()
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
                summary = summarize_text(content)

                if summary:
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
    # Load and sanitize feeds.txt
    feeds = []
    with open("feeds.txt") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # remove inline comments like: url   # comment
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if line:
                feeds.append(line)

    categorized_articles = fetch_and_summarize(feeds)

    # Print results (for now)
    for cat, articles in categorized_articles.items():
        print(f"\n### {cat} ###")
        for art in articles:
            print(f"- {art['title']}\n  📝 {art['summary']}\n  🔗 {art['link']}")
