import feedparser
from newspaper import Article
from transformers import pipeline

# -------------------------------
# Setup summarizer
# -------------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Fetch full article text with fallback
# -------------------------------
def fetch_article_content(entry):
    url = entry.link
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text.strip()

        # Fallback to RSS summary if article too short
        if len(text.split()) < 50:
            rss_summary = getattr(entry, "summary", "").strip()
            if len(rss_summary.split()) >= 30:
                print(f"⚠ Using RSS summary for {url}")
                return rss_summary
            else:
                print(f"⚠ Skipping article: too short ({len(text.split())} words) - {url}")
                return None
        return text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None

# -------------------------------
# Summarize text with chunking
# -------------------------------
def chunk_text(text, max_words=400):
    """Split text into chunks of ~max_words words."""
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

def summarize_text(text, max_len=130, min_len=30):
    if not text:
        return None
    try:
        word_count = len(text.split())
        if word_count < 30:
            return None

        summaries = []
        for chunk in chunk_text(text):
            adjusted_max_len = min(max_len, max(10, len(chunk.split()) // 2))
            adjusted_min_len = min(min_len, max(5, adjusted_max_len // 2))

            summary = summarizer(
                chunk,
                max_length=adjusted_max_len,
                min_length=adjusted_min_len,
                do_sample=False
            )
            summaries.append(summary[0]["summary_text"])

        # Merge multi-chunk summaries into final summary
        if len(summaries) > 1:
            final_summary = summarizer(
                " ".join(summaries),
                max_length=max_len,
                min_length=min_len,
                do_sample=False
            )[0]["summary_text"]
            return final_summary
        return summaries[0]
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
            for entry in feed.entries[:5]:
                title = entry.title
                content = fetch_article_content(entry)
                if not content:
                    continue

                summary = summarize_text(content)
                if not summary:
                    continue

                category = categorize_article(title, summary)
                categorized[category].append({
                    "title": title,
                    "summary": summary,
                    "link": entry.link
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
