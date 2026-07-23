#!/usr/bin/env python3
"""퍼피도감 블로그 글 목록 수집기 — 네이버 블로그 RSS
전체 글 목록(제목, 링크, 발행일, 요약)을 data/blog_posts.json 으로 저장.
"""
import json, os, re, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

BLOG_ID = "mmin_vely_00"
RSS_URL = f"https://rss.blog.naver.com/{BLOG_ID}.xml"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

req = urllib.request.Request(RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=20) as r:
    xml = r.read().decode("utf-8", errors="replace")

TAG = re.compile(r"<[^>]+>")

posts = []
root = ET.fromstring(xml)
for item in root.iter("item"):
    def text(tag):
        el = item.find(tag)
        return (el.text or "").strip() if el is not None else ""

    desc = TAG.sub("", text("description")).strip()
    posts.append({
        "title": text("title"),
        "link": text("link"),
        "pub_date": text("pubDate"),
        "summary": desc[:300],
    })

kst = timezone(timedelta(hours=9))
out = {
    "collected_at": datetime.now(kst).strftime("%Y-%m-%d %H:%M"),
    "blog_id": BLOG_ID,
    "post_count": len(posts),
    "posts": posts,
}
with open(os.path.join(DATA_DIR, "blog_posts.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"블로그 글 {len(posts)}건 수집 완료")
