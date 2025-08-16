import os, re, time, hashlib, feedparser, requests
from bs4 import BeautifulSoup
from pathlib import Path
from transformers import pipeline

STYLE_PREFIX = "In one sentence: "
STYLE_SUFFIX = ""

MAX_ITEMS = 40
PER_FEED_LIMIT = 5

feeds = [line.strip().split()[0] for line in open("feeds.txt") if line.strip() and not line.strip().startswith("#")]

summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style"]): tag.decompose()
    return soup.get_text(" ", strip=True)

def fetch_article(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 200:
            return clean_html(r.text)
    except Exception:
        return ""
    return ""

def summarize_text(text):
    text = text.strip()
    if not text:
        return ""
    try:
        s = summarizer(text[:1000], max_length=40, min_length=10, do_sample=False)
        return s[0]["summary_text"]
    except Exception:
        return text[:120]

def main():
    entries = []
    for feed in feeds:
        d = feedparser.parse(feed)
        count = 0
        for e in d.entries[:PER_FEED_LIMIT]:
            title = e.get("title","").strip()
            link = e.get("link","").strip()
            if not link or not title:
                continue
            text = fetch_article(link)
            summ = summarize_text(text) if text else title
            domain = re.sub(r"^https?://(www\.)?","",link).split("/")[0]
            line = f"- {title} — {STYLE_PREFIX}{summ}{STYLE_SUFFIX} (via {domain})"
            entries.append((time.mktime(e.published_parsed) if hasattr(e,"published_parsed") else time.time(), line, link))
            count += 1
            if count >= PER_FEED_LIMIT:
                break

    entries.sort(key=lambda x: x[0], reverse=True)
    entries = entries[:MAX_ITEMS]

    docs = Path("docs")
    docs.mkdir(exist_ok=True)

    # index.md
    out = ["# India One-Liner News\n"]
    out += [e[1] for e in entries]
    (docs/"index.md").write_text("\n".join(out), encoding="utf-8")

    # rss.xml (minimal)
    rss_items = []
    for _, line, link in entries:
        rss_items.append(f"<item><title>{line}</title><link>{link}</link></item>")
    rss = f"<?xml version='1.0'?><rss version='2.0'><channel><title>India One-Liners</title>{''.join(rss_items)}</channel></rss>"
    (docs/"rss.xml").write_text(rss, encoding="utf-8")

if __name__ == "__main__":
    main()
