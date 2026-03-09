#!/usr/bin/env python3
"""🦎 Crested Gecko Community - Daily Briefing (Claude API 없음)"""
import os, re, json, datetime, subprocess, requests

OPENWEATHER_KEY    = os.environ["OPENWEATHER_API_KEY"]
NAVER_CLIENT_ID    = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET= os.environ["NAVER_CLIENT_SECRET"]

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
    ("Seoul","KR"),("Busan","KR"),("Daegu","KR"),
    ("Daejeon","KR"),("Gwangju","KR"),("Jeju","KR"),
]

def get_weather():
    print("  날씨 수집 중...")
    cities_data = []
    for city, country in CITIES:
        try:
            r = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": f"{city},{country}", "appid": OPENWEATHER_KEY,
                        "units": "metric", "lang": "kr"},
                timeout=10
            ).json()
            icon = OWM_ICON.get(r["weather"][0]["icon"], "🌤")
            cities_data.append({
                "name": CITY_KO.get(city, city),
                "high": f"{round(r['main']['temp_max'])}°",
                "low":  f"{round(r['main']['temp_min'])}°",
                "icon": icon,
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
    print(f"  → 도시 {len(cities_data)}개, 주간예보 {len(weekly)}일")
    return {"overview": overview, "detail": "OpenWeatherMap 제공", "cities": cities_data, "weekly": weekly}


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
# 3. video_contents.txt 읽기
# ───────────────────────────────────────
def get_videos():
    videos = []
    try:
        with open("video_contents.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                url   = parts[0] if len(parts) > 0 else ""
                title = parts[1] if len(parts) > 1 else "게코 영상"
                if not url:
                    continue
                # YouTube Shorts → embed URL 변환
                vid = ""
                m = re.search(r"shorts/([A-Za-z0-9_-]+)", url)
                if m:
                    vid = m.group(1)
                else:
                    m = re.search(r"[?&]v=([A-Za-z0-9_-]+)", url)
                    if m:
                        vid = m.group(1)
                    else:
                        m = re.search(r"youtu\.be/([A-Za-z0-9_-]+)", url)
                        if m:
                            vid = m.group(1)
                if vid:
                    videos.append({
                        "title":   title,
                        "embed":   f"https://www.youtube.com/embed/{vid}",
                        "url":     url,
                    })
        print(f"  → 영상 {len(videos)}개 로드")
    except FileNotFoundError:
        print("  ⚠️ video_contents.txt 없음 — 영상 섹션 생략")
    return videos


# ───────────────────────────────────────
# 4. HTML 조립
# ───────────────────────────────────────
def build_html(weather, eco, pol, videos, date_info):

    # 도시 날씨
    cities_html = ""
    for c in weather.get("cities", []):
        cities_html += f"""<div class="city-card">
          <div class="city-name">{c['name']}</div>
          <div class="city-high">{c['high']}</div>
          <div class="city-low">{c['low']}</div>
          <div class="city-icon">{c['icon']}</div>
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
<div class="sec-hd"><span class="sec-hd-label">YouTube</span><div class="sec-hd-line"></div><span class="sec-tag tag-yt">🦎 게코 Shorts</span></div>
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
<title>🦎 크레스티드 게코 커뮤니티 아침 브리핑 · {date_info['date_ko']}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&family=Noto+Serif+KR:wght@900&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:'Noto Sans KR',sans-serif;display:flex;justify-content:center;padding:16px}}
.card{{width:100%;max-width:480px;border-radius:16px;overflow:hidden;background:#161b22;box-shadow:0 8px 32px rgba(0,0,0,.5)}}
.hd{{background:linear-gradient(135deg,#1a2332,#0d1f35);padding:24px;position:relative;overflow:hidden}}
.hd::before{{content:'🦎';position:absolute;right:-10px;top:-10px;font-size:80px;opacity:.08}}
.hd-eyebrow{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:#58a6ff;text-transform:uppercase;margin-bottom:4px}}
.hd-title{{font-family:'Noto Serif KR',serif;font-size:26px;font-weight:900;color:#fff}}
.hd-sub{{font-size:11px;color:rgba(255,255,255,.4);margin-top:4px}}
.hd-inner{{display:flex;justify-content:space-between;align-items:flex-start}}
.hd-date-big{{font-family:'DM Mono',monospace;font-size:52px;font-weight:700;color:#58a6ff;line-height:1}}
.hd-date-small{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.4);text-align:right;letter-spacing:.08em}}
.promo-banner{{background:linear-gradient(160deg,#0a1f08,#1a3a15,#0e2a0a);border-bottom:3px solid #3d7a3a}}
.promo-inner{{padding:22px 24px 20px}}
.promo-badge-row{{display:flex;align-items:center;gap:8px;margin-bottom:14px}}
.promo-badge{{background:#3d7a3a;color:#c8f0a0;font-size:9px;letter-spacing:.12em;text-transform:uppercase;padding:3px 10px;border-radius:20px}}
.promo-badge-line{{flex:1;height:1px;background:rgba(255,255,255,.08)}}
.promo-copy{{text-align:center;margin-bottom:18px}}
.promo-heart{{font-size:28px;display:block;margin-bottom:8px;animation:hb 1.8s ease infinite}}
@keyframes hb{{0%,100%{{transform:scale(1)}}30%{{transform:scale(1.18)}}70%{{transform:scale(1.1)}}}}
.promo-main-text{{font-size:18px;font-weight:900;color:#fff;line-height:1.55;margin-bottom:6px}}
.promo-main-text em{{color:#7ae050;font-style:normal}}
.promo-sub-text{{font-size:13px;color:rgba(255,255,255,.65);line-height:1.7}}
.promo-sub-text strong{{color:#a8e060}}
.promo-org-box{{background:rgba(106,173,69,.12);border:1px solid rgba(106,173,69,.35);border-radius:8px;padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px}}
.promo-org-name{{font-size:16px;font-weight:900;color:#fff;display:flex;align-items:center;gap:6px;margin-bottom:4px}}
.promo-org-url{{font-size:11px;color:#6aad45;text-decoration:none;border-bottom:1px solid rgba(106,173,69,.4)}}
.promo-qr-emoji{{font-size:36px}}
.promo-qr-label{{font-size:9px;color:rgba(255,255,255,.3);display:block;text-align:center}}
.promo-img-wrap{{border-radius:8px;overflow:hidden;border:1px solid rgba(106,173,69,.25)}}
.promo-img-wrap img{{width:100%;display:block}}
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
.cities{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:0 16px 16px}}
.city-card{{background:#0d1117;border-radius:8px;padding:10px 8px;text-align:center;border:1px solid rgba(255,255,255,.06)}}
.city-name{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.1em;color:#58a6ff;margin-bottom:4px}}
.city-high{{font-size:16px;font-weight:700;color:#e6edf3}}
.city-low{{font-size:11px;color:rgba(255,255,255,.4);margin-bottom:2px}}
.city-icon{{font-size:18px}}
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
</style>
</head>
<body>
<div class="card">

<!-- HEADER -->
<div class="hd">
  <div class="hd-inner">
    <div>
      <div class="hd-eyebrow">Crested Gecko Community</div>
      <div class="hd-title">🦎 아침 브리핑</div>
      <div class="hd-sub">날씨 · 경제 · 정치 · 운세 · 유튜브</div>
    </div>
    <div>
      <div class="hd-date-big">{date_info['day_num']}</div>
      <div class="hd-date-small">{date_info['date_en']}</div>
    </div>
  </div>
</div>

<!-- PROMO -->
<div class="promo-banner"><div class="promo-inner">
  <div class="promo-badge-row"><span class="promo-badge">🌿 함께해요</span><div class="promo-badge-line"></div><span class="promo-badge">파충류 권익 보호</span></div>
  <div class="promo-copy">
    <span class="promo-heart">♥️</span>
    <div class="promo-main-text">생명을 소중히 여기신다면<br><em>함께해 주시고 힘을 실어주세요</em></div>
    <div class="promo-sub-text"><strong>집사님들이 관심을 가져주셔야!</strong><br>더 좋은 환경에서 키우실 수 있습니다! 🦎</div>
  </div>
  <div class="promo-org-box">
    <div>
      <div class="promo-org-name">사단법인 작은생명공존연합 <span>‼️</span></div>
      <a class="promo-org-url" href="https://www.littlelives.or.kr/" target="_blank">🔗 www.littlelives.or.kr</a>
    </div>
    <div><div class="promo-qr-emoji">🐊</div><span class="promo-qr-label">Little Lives</span></div>
  </div>
  <div class="promo-img-wrap"><img src="images/littlelives.png" alt="작은생명공존연합"></div>
</div></div>

<!-- WEATHER -->
<div class="sec-hd"><span class="sec-hd-label">Weather</span><div class="sec-hd-line"></div><span class="sec-tag tag-weather">전국 날씨</span></div>
<div class="weather-ov">
  <div class="weather-ov-icon">🌤</div>
  <div>
    <div class="weather-ov-title">{weather.get('overview','')}</div>
    <div class="weather-ov-sub">{weather.get('detail','')}</div>
  </div>
</div>
<div class="cities">{cities_html}</div>
<div class="weekly">{weekly_html}</div>

<!-- ECONOMY NEWS -->
<div class="sec-hd"><span class="sec-hd-label">Economy</span><div class="sec-hd-line"></div><span class="sec-tag tag-eco">경제·주식</span></div>
<div class="news-list">{news_items(eco)}</div>

<!-- POLITICS NEWS -->
<div class="sec-hd"><span class="sec-hd-label">Politics</span><div class="sec-hd-line"></div><span class="sec-tag tag-pol">정치·사회</span></div>
<div class="news-list">{news_items(pol)}</div>

<!-- ZODIAC (이미지) -->
<div class="sec-hd"><span class="sec-hd-label">Zodiac</span><div class="sec-hd-line"></div><span class="sec-tag tag-zod">띠별 · 별자리 운세</span></div>
<div class="fortune-img">
  <img src="images/zodiac.jpg" alt="띠별 운세"
       onerror="this.parentElement.innerHTML='<div class=\\'fortune-empty\\'>🔮 오늘의 운세 이미지 준비 중<br><small>images/zodiac.jpg 업로드 해주세요</small></div>'">
</div>
<div class="fortune-img">
  <img src="images/horoscope.jpg" alt="별자리 운세"
       onerror="this.parentElement.innerHTML='<div class=\\'fortune-empty\\'>⭐ 별자리 운세 이미지 준비 중<br><small>images/horoscope.jpg 업로드 해주세요</small></div>'">
</div>
{yt_section}

<!-- FOOTER -->
<div class="footer">
  🦎 Crested Gecko Community · {date_info['date_ko']}<br>
  날씨 제공: OpenWeatherMap · 뉴스 제공: 네이버 검색
</div>

</div>
<script>
function showVid(i) {{
  document.querySelectorAll('.mtab').forEach((t,idx) => t.classList.toggle('active', idx===i));
  document.querySelectorAll('.mpanel').forEach((p,idx) => p.classList.toggle('active', idx===i));
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

    print("\n📺 [3/4] 영상 로드...")
    videos = get_videos()

    print("\n🏗️  [4/4] HTML 조립 및 푸시...")
    html = build_html(weather, eco, pol, videos, date_info)
    push(html, date_info["date_str"])

    print("\n" + "=" * 50)
    print(f"🎉 완료! Claude API 비용: $0")
    print(f"   URL: https://크레노트.com?d={now.strftime('%Y%m%d')}")

if __name__ == "__main__":
    main()
