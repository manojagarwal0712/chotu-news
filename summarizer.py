import feedparser
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from transformers import pipeline
from newspaper import Article
import os
from datetime import datetime

# Summarizer pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Keyword-based categorization rules
CATEGORIES = {
    "India – Crime & Security": ["terror", "gang", "murder", "attack", "crime", "police", "killed", "death", "crash", "accident", "search"],
    "Science & Space": ["isro", "nasa", "satellite", "space", "launch", "rocket"],
    "Politics & Governance": ["modi", "bjp", "congress", "minister", "election", "cm", "government", "parliament", "statehood"],
    "Economy & Public Interest": ["bank", "economy", "holiday", "inflation", "stock", "market"],
    "Technology & Innovation": ["ai", "google", "meta", "microsoft", "apple", "technology", "tech", "pixel", "iphone", "cyber", "scam", "tv"],
    "Business & Thought Leadership": ["startup", "capital", "investor", "founder", "business", "market", "funding"],
}

def categorize(text):
    text_lower = text.lower()
    for category, keywords in CATEGORIES.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "Miscellaneous"

def fetch_article_summary(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        full_text = article.text

        # Hugging Face summarizer
        summary = summarizer(full_text, max_length=180, min_length=60, do_sample=False)[0]['summary_text']
        return summary
    except Exception as e:
        return f"Error fetching article: {e}"

def fetch_and_summarize(feeds):
    categorized_articles = {}

    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:  # limit to 10 per feed
            title = entry.title
            link = entry.link
            summary = fetch_article_summary(link)
            combined_text = f"{title} — {summary}"
            category = categorize(combined_text)

            if category not in categorized_articles:
                categorized_articles[category] = []
            categorized_articles[category].append(f"- **{title}** ({link})\n  {summary}")

    return categorized_articles

def save_markdown(categorized_articles, output_file="docs/index.md"):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 📰 Chotu News — {datetime.now().strftime('%B %d, %Y')}\n\n")
        for category, articles in categorized_articles.items():
            f.write(f"## {category}\n")
            f.write("\n".join(articles))
            f.write("\n\n")

if __name__ == "__main__":
    # Load feeds.txt
    with open("feeds.txt", "r") as f:
        feeds = [line.strip() for line in f if line.strip()]

    categorized_articles = fetch_and_summarize(feeds)
    save_markdown(categorized_articles)
    print("✅ News summaries updated in docs/index.md")
