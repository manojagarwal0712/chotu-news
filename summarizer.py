import feedparser
from newspaper import Article
from transformers import pipeline
import os
import re

# -------------------------------
# Init summarizer (Hugging Face)
# -------------------------------
summarizer = pipeline(
    "summarization",
    model="sshleifer/distilbart-cnn-12-6",
    tokenizer="sshleifer/distilbart-cnn-12-6",
    framework="pt"  # torch
)

# -------------------------------
# Categorization rules (fast, lightweight)
# -------------------------------
CATEGORIES = {
    "Politics": ["election", "government", "minister", "policy", "parliament", "bjp", "congress"],
    "Markets": ["stock", "market", "nifty", "sensex", "shares", "ipo", "trading", "sebi"],
    "Startups": ["startup", "funding", "venture", "founder", "unicorn", "seed round", "accelerator"],
    "Tech": ["AI", "software", "app", "gadget", "tech", "smartphone", "internet", "cyber", "semiconductor"],
    "Sports": ["cricket", "football", "hockey", "tournament", "match", "score", "ipl", "olympics"],
    "Default": []
}

# -------------------------------
# Clean and categorize helpers
# -------------------------------
def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def categorize(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    for cat, keywords in CATEGORIES.items():
        if any(kw.lower() in text for kw in keywords):
            return cat
    return "Default"

# -------------------------------
# Summarization helper
# -------------------------------
def summarize_text(text: str, max_len: int = 80) -> str:
    try:
        result = summarizer(text, max_length=max_len, min_length=20, do_sample=False)
        return clean_text(result[0]['summary_text'])
    except Exception as e:
        return clean_text(text[:200])  # fallback: truncate

# -------------------------------
# Fetch + Summarize
# -------------------------------
def fetch_and_summarize(feed_urls):
    articles = []
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # limit per feed
                url = entry.link
                try:
                    article = Article(url)
                    article.download()
                    article.parse()
                    article.nlp()
                except Exception:
                    continue

                summary = summarize_text(article.text)
                category = categorize(article.title, summary)

                articles.append({
                    "title": clean_text(article.title),
                    "url": url,
                    "summary": summary,
                    "category": category
                })
        except Exception as e:
            print(f"❌ Failed to parse {feed_url}: {e}")
    return articles

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    # Load and sanitize feeds.txt
    with open("feeds.txt") as f:
        feeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    categorized_articles = fetch_and_summarize(feeds)

    # Group by category
    grouped = {}
    for art in categorized_articles:
        grouped.setdefault(art["category"], []).append(art)

    # Write Markdown to doc/index.md
    os.makedirs("doc", exist_ok=True)
    with open("doc/index.md", "w", encoding="utf-8") as f:
        f.write("# 📰 Daily News Digest\n\n")
        for cat, arts in grouped.items():
            f.write(f"## {cat}\n\n")
            for a in arts:
                f.write(f"### [{a['title']}]({a['url']})\n\n")
                f.write(f"{a['summary']}\n\n")
