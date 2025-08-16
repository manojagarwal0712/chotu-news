# India One-Liner News Blog

This project auto-summarizes India-first news (tech, startups, politics, markets) into one-liners.

### How it works
- Pulls RSS feeds from `feeds.txt`
- Fetches articles, cleans text
- Summarizes into "In one sentence: ..." style
- Publishes to GitHub Pages (docs/index.md + docs/rss.xml)
- Optionally cross-posts to Blogger

### Quick setup
1. Create a new GitHub repo and upload these files
2. Enable GitHub Pages (Settings → Pages → Deploy from branch → main → /docs)
3. (Optional) Add GitHub Secrets for Blogger cross-posting:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REFRESH_TOKEN`
   - `BLOGGER_BLOG_ID`
4. That's it! Workflow runs 06:00, 12:00, 18:00 IST daily.

### Local run
```bash
pip install -r requirements.txt
python summarizer.py
```

Output is written into `docs/index.md` (for Pages) and `docs/rss.xml`.
