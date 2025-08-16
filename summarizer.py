import feedparser
import re
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from markdownify import markdownify as md

# Load summarizer once (distilbart is light & works well)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# --- Utility functions ---

def clean_text(text: str) -> str:
    """Remove HTML and extra spaces."""
    text = md(text or "")
    return re.sub(r"\s+", " ", text).strip()

def bold_numbers(text: str) -> str:
    """Highlight numbers/lakh/crore with bold for readability."""
    return re.sub(r"(\b\d[\d,\.]*\s?(?:lakh|crore|cr|₹|usd|%|million|billion)?)",
                  r"**\1**", text, flags=re.I)

def summarize_text(text: str) -> str:
    """Generate a short summary using HF model."""
    if not text:
        return ""
    try:
        summary = summarizer(text, max_length=30, min_length=10, do_sample=False)
        return summary[0]["summary_text"].strip()
    except Exception:
        return text[:200]  # fallback

def extract_official_link(summary_html: str) -> str:
    """Look for gov.in / nic.in / .pdf links inside description."""
    soup = BeautifulSoup(summary_html or "", "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(x in href for x in [".pdf", "gov.in", "nic.in"]):
            return href
    return None

# --- Main function ---

def fetch_and_summarize(feeds, limit=5):
    all_lines = []
    for feed_url in feeds:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            title = clean_text(entry.get("title", ""))
            desc = clean_text(entry.get("summary", ""))
            link = entry.get("link", "")

            # Try to summarize description
            summary = summarize_text(desc) if desc else ""
            if not summary or summary.lower().startswith("in one sentence"):
                final_text = title
            else:
                final_text = summary

            final_text = bold_numbers(final_text)

            # Add source
            domain = re.sub(r"^https?://(www\.)?", "", link).split("/")[0]
            source_link = f"[{domain}](https://{domain})"

            # Check for official notification
            official = extract_official_link(entry.get("summary", ""))
            if official:
                line = f"- {final_text} [📄 Details here]({official}) · via {source_link}"
            else:
                line = f"- {final_text} (via {source_link})"

            all_lines.append(line)
    return all_lines

if __name__ == "__main__":
    feeds = []
    with open("feeds.txt") as f:
        feeds = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    lines = fetch_and_summarize(feeds, limit=7)

    output_md = "# India One-Liner News\n\n" + "\n".join(lines)
    with open("docs/news.md", "w", encoding="utf-8") as f:
        f.write(output_md)

    print("✅ News summary updated.")
