import feedparser
from newspaper import Article
from transformers import pipeline

# -------------------------------
# Setup summarizer
# -------------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Fetch full article text
# -------------------------------
def fetch_article_content(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()

        if len(text.split()) < 50:
            print(f"⚠ Skipping article: too short ({len(text.split())} words) - {url}")
            return None
        return text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None

# -------------------------------
# Summarize text with automatic max_length adjustment
# -------------------------------
def summarize_text(text, max_len=130, min_len=30):
    if not text:
        return None
    try:
        word_count = len(text.split())
        if word_count < 50:
            print(f"⚠ Skipping article: too short ({word_count} words)")
            return None

        # Adjust max_length based on input length
        adjusted_max_len = min(max_len, max(10, word_count // 2))
        summary = summarizer(
            text,
            max_length=adjusted_max_len,
            min_length=min_len,
            do_sample=False
        )
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
            for entry in feed.entries[:5]:  # Fetch up to 5 articles per feed
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
