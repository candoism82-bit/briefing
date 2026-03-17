#!/usr/bin/env python3
"""🦎 Crested Gecko Community - Daily Briefing (Claude API 없음)"""
import os, re, json, datetime, subprocess, requests

OPENWEATHER_KEY    = os.environ["OPENWEATHER_API_KEY"]
NAVER_CLIENT_ID    = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET= os.environ["NAVER_CLIENT_SECRET"]
YOUTUBE_API_KEY    = os.environ.get("YOUTUBE_API_KEY", "")

# ───────────────────────────────────────
# 날씨 아이콘 / 도시명 변환
# ───────────────────────────────────────
CITY_KO = {
    "Seoul":"서울","Busan":"부산","Daegu":"대구",
    "Daejeon":"대전","Gwangju":"광주","Jeju":"제주"
}
OWM_ICON = {
    "01d":"☀️","01n":"🌙","02d":"⛅","02n":"⛅",
    "03d":"🌥","03n":"🌥","04d":"☁️","04n":"☁️",
    "09d":"🌧️","09n":"🌧️","10d":"🌦","10n":"🌦",
    "11d":"⛈️","11n":"⛈️","13d":"❄️","13n":"❄️",
    "50d":"🌫️","50n":"🌫️",
}
DAYS_KO = ["월","화","수","목","금","토","일"]

# ───────────────────────────────────────
# 1. OpenWeatherMap 날씨
# ───────────────────────────────────────
CITIES = [
    ("Seoul",   "KR", 37.5665, 126.9780),
    ("Busan",   "KR", 35.1796, 129.0756),
    ("Daegu",   "KR", 35.8714, 128.6014),
    ("Daejeon", "KR", 36.3504, 127.3845),
    ("Gwangju", "KR", 35.1595, 126.8526),
    ("Jeju",    "KR", 33.4996, 126.5312),
]

# 미세먼지 등급
def dust_grade(pm, thresholds, labels):
    for t, l in zip(thresholds, labels):
        if pm <= t:
            return l
    return labels[-1]

def pm10_grade(v):
    return dust_grade(v, [30,80,150], ["😊 좋음","🙂 보통","😷 나쁨","🚨 매우나쁨"])

def pm25_grade(v):
    return dust_grade(v, [15,35,75], ["😊 좋음","🙂 보통","😷 나쁨","🚨 매우나쁨"])

def get_weather():
    print("  날씨 수집 중...")
    cities_data = []
    for city, country, lat, lon in CITIES:
        try:
            r = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": f"{city},{country}", "appid": OPENWEATHER_KEY,
                        "units": "metric", "lang": "kr"},
                timeout=10
            ).json()
            icon = OWM_ICON.get(r["weather"][0]["icon"], "🌤")
            # 미세먼지
            ar = requests.get(
                "http://api.openweathermap.org/data/2.5/air_pollution",
                params={"lat": lat, "lon": lon, "appid": OPENWEATHER_KEY},
                timeout=10
            ).json()
            comp = ar["list"][0]["components"]
            pm10 = round(comp.get("pm10", 0))
            pm25 = round(comp.get("pm2_5", 0))
            cities_data.append({
                "name": CITY_KO.get(city, city),
                "high": f"{round(r['main']['temp_max'])}°",
                "low":  f"{round(r['main']['temp_min'])}°",
                "icon": icon,
                "pm10": pm10,
                "pm25": pm25,
                "pm10_grade": pm10_grade(pm10),
                "pm25_grade": pm25_grade(pm25),
            })
        except Exception as e:
            print(f"  ⚠️ {city} 날씨 오류: {e}")

    # 서울 주간 예보 (forecast API)
    weekly = []
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": "Seoul,KR", "appid": OPENWEATHER_KEY,
                    "units": "metric", "lang": "kr", "cnt": 40},
            timeout=10
        ).json()
        # 날짜별 최고/최저 집계
        day_map = {}
        for item in r["list"]:
            dt   = datetime.datetime.fromtimestamp(item["dt"])
            key  = dt.strftime("%m/%d")
            day  = DAYS_KO[dt.weekday()]
            icon = OWM_ICON.get(item["weather"][0]["icon"], "🌤")
            if key not in day_map:
                day_map[key] = {"day": f"{key}({day})", "icon": icon,
                                "high": item["main"]["temp_max"],
                                "low":  item["main"]["temp_min"]}
            else:
                day_map[key]["high"] = max(day_map[key]["high"], item["main"]["temp_max"])
                day_map[key]["low"]  = min(day_map[key]["low"],  item["main"]["temp_min"])
        for k, v in list(day_map.items())[:7]:
            weekly.append({
                "day":  v["day"],
                "icon": v["icon"],
                "high": f"{round(v['high'])}°",
                "low":  f"{round(v['low'])}°",
            })
    except Exception as e:
        print(f"  ⚠️ 주간예보 오류: {e}")

    # 오늘 서울 날씨 요약
    overview = f"서울 현재 {cities_data[0]['low']}~{cities_data[0]['high']}" if cities_data else "날씨 준비 중"
    seoul_pm = {
        "pm10":       cities_data[0].get("pm10",  0) if cities_data else 0,
        "pm25":       cities_data[0].get("pm25",  0) if cities_data else 0,
        "pm10_grade": cities_data[0].get("pm10_grade", "") if cities_data else "",
        "pm25_grade": cities_data[0].get("pm25_grade", "") if cities_data else "",
    }
    print(f"  → 도시 {len(cities_data)}개, 주간예보 {len(weekly)}일")
    return {"overview": overview, "detail": "OpenWeatherMap 제공", "cities": cities_data, "weekly": weekly, "seoul_pm": seoul_pm}


# ───────────────────────────────────────
# 2. 네이버 뉴스 검색
# ───────────────────────────────────────
def naver_news(query, display=4):
    headers = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    r = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        params={"query": query, "display": display, "sort": "date"},
        headers=headers, timeout=10
    ).json()
    items = []
    for item in r.get("items", []):
        title   = re.sub(r"<[^>]+>", "", item["title"])
        desc    = re.sub(r"<[^>]+>", "", item["description"])
        source  = re.sub(r"https?://(www\.)?", "", item["originallink"]).split("/")[0]
        items.append({
            "title":   title,
            "summary": desc,
            "url":     item["originallink"] or item["link"],
            "source":  source,
        })
    return items

def get_news():
    print("  뉴스 수집 중...")
    try:
        eco = naver_news("주식 경제 코스피", 4)
        pol = naver_news("정치 사회 뉴스", 4)
        print(f"  → 경제 {len(eco)}건, 정치 {len(pol)}건")
        return eco, pol
    except Exception as e:
        print(f"  ⚠️ 뉴스 오류: {e}")
        return [], []


# ───────────────────────────────────────
# 3. YouTube 인기 Shorts TOP 3 (카테고리별 검색)
# ───────────────────────────────────────
import re as _re

def _parse_duration(iso):
    m = _re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
    if not m: return 9999
    return int(m.group(1) or 0)*3600 + int(m.group(2) or 0)*60 + int(m.group(3) or 0)

def get_videos():
    videos = []
    if not YOUTUBE_API_KEY:
        print("  ⚠️ YOUTUBE_API_KEY 없음 — 영상 섹션 생략")
        return videos

    # 검색 키워드 (카테고리별 1개씩 가져옴)
    QUERIES = [
        "크레스티드게코 shorts -동요 -어린이 -kids",
        "동물 귀여운 shorts -동요 -어린이 -kids",
        "웃긴영상 shorts -동요 -어린이 -kids",
    ]

    try:
        print("  ▶ YouTube Shorts 검색 중...")
        seen = set()
        for query in QUERIES:
            # 검색 API로 최신 인기 Shorts 탐색
            sr = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part":        "snippet",
                    "q":           query,
                    "type":        "video",
                    "videoDuration": "short",
                    "regionCode":  "KR",
                    "relevanceLanguage": "ko",
                    "order":       "viewCount",
                    "safeSearch":  "moderate",
                    "maxResults":  5,
                    "key":         YOUTUBE_API_KEY,
                },
                timeout=15
            ).json()

            # 제목에 어린이/동요 관련 키워드 있으면 제외
            EXCLUDE_WORDS = ["동요", "어린이", "kids", "유아", "아기", "nursery",
                             "children", "동화", "뽀로로", "핑크퐁", "baby shark"]

            for item in sr.get("items", []):
                vid   = item["id"].get("videoId", "")
                title = item["snippet"]["title"]
                if not vid or vid in seen:
                    continue
                # 제목 필터링
                if any(w.lower() in title.lower() for w in EXCLUDE_WORDS):
                    continue
                # contentDetails로 실제 duration 확인 (60초 이하 = Shorts)
                dr = requests.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "contentDetails", "id": vid, "key": YOUTUBE_API_KEY},
                    timeout=10
                ).json()
                items_d = dr.get("items", [])
                if not items_d:
                    continue
                duration = _parse_duration(items_d[0]["contentDetails"]["duration"])
                if duration <= 60:
                    seen.add(vid)
                    videos.append({
                        "title": title,
                        "embed": f"https://www.youtube.com/embed/{vid}",
                        "url":   f"https://www.youtube.com/shorts/{vid}",
                    })
                    break  # 카테고리당 1개만

        print(f"  → 영상 {len(videos)}개 로드")
    except Exception as e:
        print(f"  ⚠️ YouTube API 오류: {e}")
    return videos


# ───────────────────────────────────────
# 4. ads_contents.txt 읽기
# ───────────────────────────────────────
def get_ads():
    ads = []
    try:
        with open("ads_contents.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 2:
                    continue
                text  = parts[0] if len(parts) > 0 else ""
                url   = parts[1] if len(parts) > 1 else "#"
                image = parts[2] if len(parts) > 2 else ""
                if text:
                    ads.append({"text": text.replace("\\n", "\n"), "url": url, "image": image})
        print(f"  → 광고 {len(ads)}개 로드")
    except FileNotFoundError:
        print("  ⚠️ ads_contents.txt 없음 — 광고 섹션 생략")
    return ads


# 5. HTML 조립
# ───────────────────────────────────────
def build_html(weather, eco, pol, videos, ads, date_info):

    # 서울 미세먼지 변수 미리 계산
    _spm = weather.get("seoul_pm", {})
    s_pm10      = _spm.get("pm10", "—")
    s_pm25      = _spm.get("pm25", "—")
    s_pm10_g    = _spm.get("pm10_grade", "")
    s_pm25_g    = _spm.get("pm25_grade", "")
    s_pm10_lbl  = s_pm10_g.split()[-1] if s_pm10_g else ""
    s_pm25_lbl  = s_pm25_g.split()[-1] if s_pm25_g else ""
    def _dust_color(g):
        if g.startswith("😊"): return "#4fc3f7"
        if g.startswith("🙂"): return "#81c784"
        if g.startswith("😷"): return "#ffb74d"
        return "#e57373"
    s_pm10_col  = _dust_color(s_pm10_g) if s_pm10_g else "#aaa"
    s_pm25_col  = _dust_color(s_pm25_g) if s_pm25_g else "#aaa"

    # 광고 탭 섹션 생성
    ads_section = ""
    if ads:
        tabs = ""
        panels = ""
        for i, ad in enumerate(ads):
            active = "active" if i == 0 else ""
            tabs += f'<div class="adtab {active}" onclick="showAd({i})">{i+1}</div>'
            img_html = f'<img src="{ad["image"]}" alt="">' if ad["image"] else ""
            link_html = f'<a class="adpanel-link" href="{ad["url"]}" target="_blank">🔗 {ad["url"]}</a>' if ad["url"] and ad["url"] != "#" else ""
            panels += f'''<div class="adpanel {active}">
  <a href="{ad['url']}" target="_blank">{img_html}</a>
  <div class="adpanel-text">{ad['text']}</div>
  {link_html}
</div>'''
        ads_section = f'''<!-- ADS -->
<div class="sec-hd"><span class="sec-hd-label">Community</span><div class="sec-hd-line"></div><span class="sec-tag tag-yt">📌 커뮤니티 소식</span></div>
<div class="ads-wrap">
  <div class="ads-tabs">{tabs}</div>
  {panels}
</div>'''

    # 도시 날씨
    cities_html = ""
    for c in weather.get("cities", []):
        pm10_g = c.get('pm10_grade','')
        pm25_g = c.get('pm25_grade','')
        cities_html += f"""<div class="city-card">
          <div class="city-name">{c['name']}</div>
          <div class="city-icon">{c['icon']}</div>
          <div class="city-high">{c['high']}</div>
          <div class="city-low">{c['low']}</div>
          <div class="city-dust"><span class="dust-label">미세</span><span class="dust-val">{c.get('pm10','—')}㎍</span><span class="dust-grade">{pm10_g.split()[1] if pm10_g else ''}</span></div>
          <div class="city-dust"><span class="dust-label">초미세</span><span class="dust-val">{c.get('pm25','—')}㎍</span><span class="dust-grade">{pm25_g.split()[1] if pm25_g else ''}</span></div>
        </div>"""

    # 주간예보
    weekly_html = ""
    for d in weather.get("weekly", []):
        weekly_html += f"""<div class="week-day">
          <div class="wd-label">{d['day']}</div>
          <div class="wd-icon">{d['icon']}</div>
          <div class="wd-high">{d['high']}</div>
          <div class="wd-low">{d['low']}</div>
        </div>"""

    # 뉴스
    def news_items(items):
        html = ""
        for i, n in enumerate(items, 1):
            html += f"""<div class="news-item">
          <span class="news-num">0{i}</span>
          <div class="news-body">
            <a class="news-title" href="{n['url']}" target="_blank">{n['title']}</a>
            <div class="news-summary">{n['summary']}</div>
            <div class="news-source">▸ {n['source']}</div>
          </div>
        </div>"""
        return html

    # YouTube 탭
    yt_tabs = ""
    yt_panels = ""
    for i, v in enumerate(videos):
        active = "active" if i == 0 else ""
        yt_tabs   += f'<button class="mtab {active}" onclick="showVid({i})">📺 Shorts {i+1}</button>'
        yt_panels += f"""<div class="mpanel {active}" id="vpanel-{i}">
          <iframe src="{v['embed']}" frameborder="0" allowfullscreen
            style="width:100%;aspect-ratio:9/16;border-radius:8px;display:block;"></iframe>
          <a class="yt-link" href="{v['url']}" target="_blank">▶ {v['title']}</a>
        </div>"""

    yt_section = ""
    if videos:
        yt_section = f"""
<!-- YOUTUBE -->
<div class="sec-hd"><span class="sec-hd-label">YouTube</span><div class="sec-hd-line"></div><span class="sec-tag tag-yt">🎬 오늘의 Shorts</span></div>
<div class="mtabs">{yt_tabs}</div>
{yt_panels}"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta property="og:type" content="website">
<meta property="og:title" content="크레오늘 아침 브리핑 · {date_info['date_ko']}">
<meta property="og:description" content="날씨 · 미세먼지 · 경제 · 정치 · 운세 · 유튜브 한 번에!">
<meta property="og:image" content="https://xn--wh1b36hvpo04j.com/images/og_banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="https://크레오늘.com">
<title>크레오늘 · CreOnel 아침 브리핑 · {date_info['date_ko']}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&family=Noto+Serif+KR:wght@900&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:'Noto Sans KR',sans-serif;display:flex;justify-content:center;padding:16px}}
.card{{width:100%;max-width:480px;border-radius:16px;overflow:hidden;background:#161b22;box-shadow:0 8px 32px rgba(0,0,0,.5)}}
.hd{{background:linear-gradient(135deg,#1a2332,#0d1f35);padding:24px;position:relative;overflow:hidden}}
.hd-logo{{width:52px;height:52px;object-fit:contain;border-radius:10px}}
.hd-eyebrow{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.12em;color:#7ec8a0;text-transform:uppercase;margin-bottom:2px}}
.hd-title{{font-family:'Noto Serif KR',serif;font-size:24px;font-weight:900;color:#fff;line-height:1.2}}
.hd-sub{{font-size:11px;color:rgba(255,255,255,.4);margin-top:4px}}
.hd-inner{{display:flex;justify-content:space-between;align-items:flex-start}}
.hd-date-big{{font-family:'DM Mono',monospace;font-size:52px;font-weight:700;color:#58a6ff;line-height:1}}
.hd-date-small{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.4);text-align:right;letter-spacing:.08em}}
.ads-wrap{{padding:0 16px 16px}}
.ads-tabs{{display:flex;gap:6px;margin-bottom:10px;overflow-x:auto;scrollbar-width:none}}
.ads-tabs::-webkit-scrollbar{{display:none}}
.adtab{{flex-shrink:0;padding:5px 12px;border-radius:20px;font-size:11px;background:rgba(255,255,255,.07);color:rgba(255,255,255,.5);cursor:pointer;border:1px solid rgba(255,255,255,.1);transition:.2s}}
.adtab.active{{background:#3d7a3a;color:#c8f0a0;border-color:#3d7a3a}}
.adpanel{{display:none;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;overflow:hidden}}
.adpanel.active{{display:block}}
.adpanel a{{display:block;text-decoration:none;color:inherit}}
.adpanel img{{width:100%;display:block;object-fit:contain}}
.adpanel-text{{padding:12px 14px;font-size:12px;color:rgba(255,255,255,.7);line-height:1.8;white-space:pre-line}}
.adpanel-link{{display:inline-block;margin:0 14px 12px;font-size:11px;color:#58a6ff}}
.sec-hd{{display:flex;align-items:center;gap:8px;padding:20px 20px 12px}}
.sec-hd-label{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:#58a6ff;text-transform:uppercase}}
.sec-hd-line{{flex:1;height:1px;background:rgba(255,255,255,.08)}}
.sec-tag{{font-size:9px;padding:2px 8px;border-radius:10px;letter-spacing:.06em}}
.tag-weather{{background:rgba(88,166,255,.15);color:#58a6ff}}
.tag-eco{{background:rgba(63,185,80,.15);color:#3fb950}}
.tag-pol{{background:rgba(248,81,73,.15);color:#f85149}}
.tag-zod{{background:rgba(210,153,34,.15);color:#d2a61a}}
.tag-yt{{background:rgba(255,166,87,.15);color:#ffa657}}
.weather-ov{{display:flex;align-items:center;gap:12px;padding:0 20px 14px}}
.weather-ov-icon{{font-size:36px}}
.weather-ov-title{{font-size:15px;font-weight:700;color:#e6edf3;margin-bottom:3px}}
.weather-ov-sub{{font-size:11px;color:rgba(255,255,255,.45);line-height:1.6}}
.ov-dust-box{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:8px 12px;min-width:110px}}
.ov-dust-title{{font-size:10px;color:rgba(255,255,255,.4);margin-bottom:5px;text-align:center;letter-spacing:.5px}}
.ov-dust-row{{display:flex;align-items:center;gap:4px;margin-bottom:3px;font-size:11px}}
.ov-dust-row:last-child{{margin-bottom:0}}
.ov-dust-lbl{{color:rgba(255,255,255,.4);min-width:30px;font-size:10px}}
.ov-dust-val{{color:rgba(255,255,255,.75);font-family:'DM Mono',monospace;font-size:11px}}
.ov-dust-grade{{font-size:10px;font-weight:700;margin-left:2px}}
.cities{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:0 16px 16px}}
.city-card{{background:#0d1117;border-radius:8px;padding:10px 8px;text-align:center;border:1px solid rgba(255,255,255,.06)}}
.city-name{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.1em;color:#58a6ff;margin-bottom:4px}}
.city-high{{font-size:16px;font-weight:700;color:#e6edf3}}
.city-low{{font-size:11px;color:rgba(255,255,255,.4);margin-bottom:2px}}
.city-icon{{font-size:18px}}
.city-dust{{display:flex;align-items:center;gap:3px;margin-top:3px;font-size:9px;line-height:1.3}}
.dust-label{{color:rgba(255,255,255,.35);min-width:26px}}
.dust-val{{color:rgba(255,255,255,.7);font-family:'DM Mono',monospace}}
.dust-grade{{color:#58a6ff;font-size:8px}}
.weekly{{display:flex;justify-content:space-between;padding:0 16px 20px;gap:4px;overflow-x:auto}}
.week-day{{flex:1;min-width:44px;text-align:center;background:#0d1117;border-radius:6px;padding:8px 4px;border:1px solid rgba(255,255,255,.06)}}
.wd-label{{font-size:9px;color:rgba(255,255,255,.5);margin-bottom:4px}}
.wd-icon{{font-size:16px;margin-bottom:4px}}
.wd-high{{font-size:12px;font-weight:700;color:#e6edf3}}
.wd-low{{font-size:10px;color:rgba(255,255,255,.35)}}
.news-list{{padding:0 16px 16px;display:flex;flex-direction:column;gap:10px}}
.news-item{{display:flex;gap:10px;background:#0d1117;border-radius:8px;padding:12px;border:1px solid rgba(255,255,255,.06)}}
.news-num{{font-family:'DM Mono',monospace;font-size:11px;color:#58a6ff;flex-shrink:0;padding-top:2px}}
.news-title{{font-size:13px;font-weight:700;color:#e6edf3;text-decoration:none;display:block;margin-bottom:4px;line-height:1.5}}
.news-title:hover{{color:#58a6ff}}
.news-summary{{font-size:11px;color:rgba(255,255,255,.55);line-height:1.6;margin-bottom:4px}}
.news-source{{font-size:10px;color:#3fb950}}
.fortune-img{{padding:0 16px 16px}}
.fortune-img img{{width:100%;border-radius:8px;display:block;border:1px solid rgba(255,255,255,.08)}}
.fortune-empty{{padding:20px 16px;text-align:center;color:rgba(255,255,255,.25);font-size:12px;background:#0d1117;border-radius:8px;margin:0 16px 16px;border:1px dashed rgba(255,255,255,.1)}}
.mtabs{{display:flex;gap:6px;padding:0 16px 12px;flex-wrap:wrap}}
.mtab{{background:#0d1117;border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:5px 12px;font-size:11px;color:rgba(255,255,255,.5);cursor:pointer;transition:.2s}}
.mtab.active{{background:rgba(255,166,87,.15);border-color:#ffa657;color:#ffa657}}
.mpanel{{display:none;padding:0 16px 16px}}
.mpanel.active{{display:block}}
.yt-link{{display:block;margin-top:8px;font-size:11px;color:#58a6ff;text-decoration:none;line-height:1.5}}
.footer{{padding:20px;text-align:center;border-top:1px solid rgba(255,255,255,.06);font-size:10px;color:rgba(255,255,255,.25);line-height:1.8}}
.footer-credit{{display:flex;align-items:center;justify-content:center;gap:8px;margin-top:10px;opacity:.7}}
.footer-credit img{{width:32px;height:32px;border-radius:50%;object-fit:cover}}
.footer-credit span{{font-size:12px;color:rgba(255,255,255,.5)}}
</style>
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-CX33EQ71Y2"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-CX33EQ71Y2');
</script>
</head>
<body>
<div class="card">

<!-- HEADER -->
<div class="hd">
  <div class="hd-inner">
    <div style="display:flex;align-items:center;gap:14px">
      <img class="hd-logo" src="images/cretoday_logo.png" alt="크레오늘">
      <div>
        <div class="hd-eyebrow">CreOnel · 크레오늘</div>
        <div class="hd-title">아침 브리핑</div>
        <div class="hd-sub">날씨 · 경제 · 정치 · 운세 · 유튜브</div>
      </div>
    </div>
    <div>
      <div class="hd-date-big">{date_info['day_num']}</div>
      <div class="hd-date-small">{date_info['date_en']}</div>
    </div>
  </div>
</div>

<!-- WEATHER -->
<div class="sec-hd"><span class="sec-hd-label">Weather</span><div class="sec-hd-line"></div><span class="sec-tag tag-weather">전국 날씨</span></div>
<div class="weather-ov">
  <div class="weather-ov-icon">🌤</div>
  <div style="flex:1">
    <div class="weather-ov-title">{weather.get('overview','')}</div>
    <div class="weather-ov-sub">{weather.get('detail','')}</div>
  </div>
  <div class="ov-dust-box">
    <div class="ov-dust-title">서울 대기질</div>
    <div class="ov-dust-row">
      <span class="ov-dust-lbl">미세</span>
      <span class="ov-dust-val">{s_pm10}㎍</span>
      <span class="ov-dust-grade" style="color:{s_pm10_col}">{s_pm10_lbl}</span>
    </div>
    <div class="ov-dust-row">
      <span class="ov-dust-lbl">초미세</span>
      <span class="ov-dust-val">{s_pm25}㎍</span>
      <span class="ov-dust-grade" style="color:{s_pm25_col}">{s_pm25_lbl}</span>
    </div>
  </div>
</div>
<div class="cities">{cities_html}</div>
<div class="weekly">{weekly_html}</div>

{yt_section}

<!-- ZODIAC (이미지) -->
<div class="sec-hd"><span class="sec-hd-label">Zodiac</span><div class="sec-hd-line"></div><span class="sec-tag tag-zod">띠별 · 별자리 운세</span></div>
<div class="fortune-img">
  <img src="images/zodiac.jpg?v={date_info['date_str'].replace('-','')}" alt="띠별 운세"
       onerror="this.parentElement.innerHTML='<div class=\\'fortune-empty\\'>🔮 오늘의 운세 이미지 준비 중<br><small>images/zodiac.jpg 업로드 해주세요</small></div>'">
</div>
<div class="fortune-img">
  <img src="images/horoscope.jpg?v={date_info['date_str'].replace('-','')}" alt="별자리 운세"
       onerror="this.parentElement.innerHTML='<div class=\\'fortune-empty\\'>⭐ 별자리 운세 이미지 준비 중<br><small>images/horoscope.jpg 업로드 해주세요</small></div>'">
</div>

<!-- ECONOMY NEWS -->
<div class="sec-hd"><span class="sec-hd-label">Economy</span><div class="sec-hd-line"></div><span class="sec-tag tag-eco">경제·주식</span></div>
<div class="news-list">{news_items(eco)}</div>

<!-- POLITICS NEWS -->
<div class="sec-hd"><span class="sec-hd-label">Politics</span><div class="sec-hd-line"></div><span class="sec-tag tag-pol">정치·사회</span></div>
<div class="news-list">{news_items(pol)}</div>

{ads_section}

<!-- FOOTER -->
<div class="footer">
  🦎 Crested Gecko Community · {date_info['date_ko']}<br>
  날씨 제공: OpenWeatherMap · 뉴스 제공: 네이버 검색
  <div class="footer-credit">
    <img src="images/kkug_cre.png" alt="kkug.cre">
    <span>Designed by @kkug.cre</span>
  </div>
</div>

</div>
<script>
function showVid(i) {{
  document.querySelectorAll('.mtab').forEach((t,idx) => t.classList.toggle('active', idx===i));
  document.querySelectorAll('.mpanel').forEach((p,idx) => p.classList.toggle('active', idx===i));
}}
function showAd(i) {{
  document.querySelectorAll('.adtab').forEach((t,idx) => t.classList.toggle('active', idx===i));
  document.querySelectorAll('.adpanel').forEach((p,idx) => p.classList.toggle('active', idx===i));
}}
(function() {{
  const d = new URLSearchParams(location.search).get('d');
  if (d && d.length === 8) {{
    const el = document.querySelector('.hd-date-big');
    if (el) el.textContent = d.slice(6,8);
  }}
}})();
</script>
</body>
</html>"""


# ───────────────────────────────────────
# 5. GitHub 푸시
# ───────────────────────────────────────
def push(html, date_str):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name",  "GitHub Actions"],     check=True)
    subprocess.run(["git", "add", "index.html"], check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("  → 변경없음, 스킵")
        return
    subprocess.run(["git", "commit", "-m", f"🦎 Daily briefing - {date_str}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("  → git push 완료")


# ───────────────────────────────────────
# Main
# ───────────────────────────────────────
def main():
    kst    = datetime.timezone(datetime.timedelta(hours=9))
    now    = datetime.datetime.now(kst)
    months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
    days_en= ["MON","TUE","WED","THU","FRI","SAT","SUN"]

    date_info = {
        "date_ko":  now.strftime("%Y년 %m월 %d일"),
        "date_en":  f"{months[now.month-1]} {now.year} · {days_en[now.weekday()]}",
        "day_num":  now.strftime("%d"),
        "date_str": now.strftime("%Y-%m-%d"),
    }

    print(f"\n🦎 브리핑 생성 시작: {date_info['date_ko']}")
    print("=" * 50)

    print("\n☁️  [1/4] 날씨 수집...")
    weather = get_weather()

    print("\n📰 [2/4] 뉴스 수집...")
    eco, pol = get_news()

    print("\n📺 [3/4] 영상 및 광고 로드...")
    videos = get_videos()
    ads    = get_ads()

    print("\n🏗️  [4/4] HTML 조립 및 푸시...")
    html = build_html(weather, eco, pol, videos, ads, date_info)
    push(html, date_info["date_str"])

    print("\n" + "=" * 50)
    print(f"🎉 완료! Claude API 비용: $0")
    print(f"   URL: https://크레오늘.com?d={now.strftime('%Y%m%d')}")

if __name__ == "__main__":
    main()
