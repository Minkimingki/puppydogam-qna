#!/usr/bin/env python3
"""퍼피도감 쓰레드 성과 수집기 — Threads API (공식)
내 전체 게시물 + 게시물별 인사이트(views/likes/replies/reposts/shares)를 수집해
data/threads_performance.json 으로 저장.
"""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
BASE = "https://graph.threads.net/v1.0"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def get_url(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


kst = timezone(timedelta(hours=9))
now = datetime.now(kst)

# 1) 전체 게시물 (페이지네이션)
posts = []
data = get("/me/threads", fields="id,text,timestamp,permalink", limit=50)
while True:
    posts.extend(data.get("data", []))
    next_url = data.get("paging", {}).get("next")
    if not next_url:
        break
    data = get_url(next_url)

# 2) 게시물별 인사이트 + 답글
METRICS = "views,likes,replies,reposts,shares"
for p in posts:
    try:
        ins = get(f"/{p['id']}/insights", metric=METRICS)
        for m in ins.get("data", []):
            name = m.get("name")
            values = m.get("values", [{}])
            p[name] = values[0].get("value", 0) if values else 0
        time.sleep(0.15)
    except Exception as e:
        p["insights_error"] = str(e)

    try:
        replies = []
        rd = get(f"/{p['id']}/replies", fields="text,username,timestamp", limit=50)
        while True:
            replies.extend(
                {"username": r.get("username"), "text": r.get("text"),
                 "timestamp": r.get("timestamp")}
                for r in rd.get("data", [])
            )
            next_url = rd.get("paging", {}).get("next")
            if not next_url:
                break
            rd = get_url(next_url)
        p["replies_list"] = replies
        time.sleep(0.15)
    except Exception as e:
        p["replies_error"] = str(e)

# 3) 토큰 만료 예정일 (60일 장기 토큰 기준 — API가 발급일을 알려주지 않으므로
#    refresh_access_token 응답의 expires_in으로 확인. 실패해도 수집엔 지장 없음)
token_expires_at = None
try:
    ref = get_url(
        "https://graph.threads.net/refresh_access_token?"
        + urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": TOKEN})
    )
    expires_in = ref.get("expires_in")
    if expires_in:
        token_expires_at = (now + timedelta(seconds=expires_in)).strftime("%Y-%m-%d")
except Exception:
    pass

out = {
    "collected_at": now.strftime("%Y-%m-%d %H:%M"),
    "token_expires_at": token_expires_at,  # None이면 확인 실패(토큰은 60일 만료형, 주기적 갱신 필요)
    "post_count": len(posts),
    "posts": posts,
}
with open(os.path.join(DATA_DIR, "threads_performance.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(f"[{now:%Y-%m-%d}] 쓰레드 게시물 {len(posts)}개 수집 완료 (토큰 만료: {token_expires_at})")
