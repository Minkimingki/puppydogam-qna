#!/usr/bin/env python3
"""퍼피도감 질문 수집기 — 네이버 지식iN 검색 API (공식)
매일 실행: 키워드별 최신 질문을 가져와 이전에 본 것과 비교, 새 질문만 저장.
"""
import json, os, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]

KEYWORDS = [
    # 견종 중심
    "말티즈 아파요", "말티즈 슬개골", "말티즈 기침",
    "비숑 피부", "비숑 아파요",
    "푸들 슬개골", "푸들 아파요",
    "포메라니안 기침", "포메 슬개골",
    # 증상 중심 (보호자가 실제로 검색하는 말)
    "강아지 슬개골 탈구", "강아지 컥컥", "강아지 마른기침",
    "강아지 다리 절뚝", "강아지 눈물자국", "강아지 물 많이",
    "강아지 소변 피", "강아지 밥을 안 먹어요", "강아지 구토",
    "강아지 심장병", "강아지 신부전", "노령견 치매",
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SEEN_PATH = os.path.join(DATA_DIR, "seen.json")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch(query, display=15, sort="date"):
    url = "https://openapi.naver.com/v1/search/kin.json?" + urllib.parse.urlencode(
        {"query": query, "display": display, "sort": sort})
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

TAG = re.compile(r"</?b>")
def clean(s):
    s = TAG.sub("", s)
    for a, b in [("&quot;", '"'), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'")]:
        s = s.replace(a, b)
    return s.strip()

seen = set()
if os.path.exists(SEEN_PATH):
    with open(SEEN_PATH, encoding="utf-8") as f:
        seen = set(json.load(f))

kst = timezone(timedelta(hours=9))
today = datetime.now(kst).strftime("%Y-%m-%d")
new_items, archive_stats = [], {}

for kw in KEYWORDS:
    try:
        data = fetch(kw)
        archive_stats[kw] = data.get("total", 0)
        for it in data.get("items", []):
            link = it["link"]
            if link in seen:
                continue
            seen.add(link)
            new_items.append({
                "keyword": kw,
                "title": clean(it["title"]),
                "desc": clean(it["description"]),
                "link": link,
            })
        time.sleep(0.2)
    except Exception as e:
        archive_stats[kw] = f"ERROR: {e}"

out_path = os.path.join(DATA_DIR, "new_questions.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"date": today, "count": len(new_items),
               "archive_stats": archive_stats, "items": new_items},
              f, ensure_ascii=False, indent=1)

# seen은 최근 5000개만 유지 (무한 성장 방지)
with open(SEEN_PATH, "w", encoding="utf-8") as f:
    json.dump(list(seen)[-5000:], f, ensure_ascii=False)

print(f"[{today}] 새 질문 {len(new_items)}건 수집 완료")
