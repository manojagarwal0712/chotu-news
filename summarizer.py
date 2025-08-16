import feedparser
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

# Initialize summarizer
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# -------------------------------
# Helper: Split text into chunks
# -------------------------------
def chunk_text(text, max_words=400):
    """Split long text into chunks to fit model limits."""
    words = text.split()
    for i in range(0, len(words), max_words):
        yield " ".join(words[i:i + max_words])

# -------------------------------
# Helper: Auto-scaled summarization
# -------------------------------
def summarize_text(text, max_len=130, min_len=30):
    """Summarize text with auto-adjusted length scaling."""
    if not text:
        return None
    try:
        word_count = len(text.split())
        if word_count < 30:
            return None

        summaries = []
        for chunk in chunk_text(text):
            chunk_len = len(chunk.split())

            # Auto-scale max/min lengths
            adjusted_max_len = min(max_len, max(20, chunk_len // 2))
            adjusted_min_len = max(min_len, adjusted_max_len // 2)

            summary = summarizer(
                chunk,
                max_length=adjusted_max_len,
                min_length=adjusted_min_len,
                do_sample=False
            )
            summaries.append(summary[0]["summary_text"])

        # Merge if multiple chunks
        if len(summaries) > 1:
            merged_text = " ".join(summaries)
            merged_len = len(merged_text.split())

            final_max_len = min(max_len, max(20, merged_len // 2))
            final_min_len = max(min_len, final_max_len // 2)

            final_summary = summarizer(
                merged_text,
                max_length=final_max_len,
                min_length=final_min_len,
                do_sample=False
            )[0]["summary_text"]

            return final_summary

        return summaries[0]

    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return None

# -------------------------------
# Helper: Fetch and clean article
# -------------------------------
def fetch_article(url):
    """Fetch raw article text from a URL."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.extract()

        # Get paragraph text
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        article_text = " ".join(paragraphs).strip()

        return article_text
    except Exception as e:
        print(f"⚠ Failed to fetch article {url}: {e}")
        return None

# -------------------------------
# Main: Process feeds
# -------------------------------
def process_feed(feed_file="feeds.txt", output_file="summaries.md"):
    """Read feeds, summarize articles, save output."""
    with open(feed_file, "r") as f:
        feed_urls = [line.strip() for line in f if line.strip()]

    all_summaries = []

    for feed_url in feed_urls:
        print(f"\n🔗 Processing feed: {feed_url}")
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:5]:  # limit to latest 5 articles per feed
            title = entry.get("title", "No Title")
            link = entry.get("link", "")
            summary = None

            # Try full article summarization
            article_text = fetch_article(link)
            if article_text:
                summary = summarize_text(article_text)

            # Fallback to RSS summary
            if not summary:
                summary = entry.get("summary", "No summary available")
                print(f"⚠ Using RSS summary for {link}")

            all_summaries.append(f"### {title}\n\n{summary}\n\n[Read more]({link})\n")

    # Save output
    with open(output_file, "w") as f:
        f.write("# Daily News Summaries\n\n")
        f.write("\n".join(all_summaries))

    print(f"\n✅ Summaries saved to {output_file}")

# -------------------------------
# Run script
# -------------------------------
if __name__ == "__main__":
    process_feed()
