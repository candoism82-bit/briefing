#!/usr/bin/env python3
"""🦎 Crested Gecko Community - Daily Briefing (Claude API 없음)"""
import os, re, json, datetime, subprocess, requests

OPENWEATHER_KEY    = os.environ.get("OPENWEATHER_API_KEY", "")
NAVER_CLIENT_ID    = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET= os.environ["NAVER_CLIENT_SECRET"]
YOUTUBE_API_KEY    = os.environ.get("YOUTUBE_API_KEY", "")
KMA_API_KEY        = os.environ.get("KMA_API_KEY", "")
AIRKOREA_API_KEY   = os.environ.get("AIRKOREA_API_KEY", "")

# ───────────────────────────────────────
# 날씨 상수
# ───────────────────────────────────────
DAYS_KO = ["월","화","수","목","금","토","일"]

# 기상청 nx/ny 격자 + 에어코리아 측정소
CITIES = [
    {"name": "서울", "nx": 60, "ny": 127, "air_station": "종로구"},
    {"name": "부산", "nx": 98, "ny": 76,  "air_station": "연제구"},
    {"name": "대구", "nx": 89, "ny": 90,  "air_station": "수성구"},
    {"name": "대전", "nx": 67, "ny": 100, "air_station": "서구"},
    {"name": "광주", "nx": 58, "ny": 74,  "air_station": "북구"},
    {"name": "제주", "nx": 52, "ny": 38,  "air_station": "이도이동"},
]

# 기상청 하늘 상태 / 강수 형태 아이콘
def kma_icon(sky, pty):
    # pty 우선: 1=비 2=비/눈 3=눈 4=소나기
    if pty == "1": return "🌧️"
    if pty == "2": return "🌨"
    if pty == "3": return "❄️"
    if pty == "4": return "🌦"
    # sky: 1=맑음 3=구름많음 4=흐림
    if sky == "1": return "☀️"
    if sky == "3": return "🌥"
    if sky == "4": return "☁️"
    return "🌤"

def pm10_grade(v):
    if v <= 30:  return "😊 좋음"
    if v <= 80:  return "🙂 보통"
    if v <= 150: return "😷 나쁨"
    return "🚨 매우나쁨"

def pm25_grade(v):
    if v <= 15:  return "😊 좋음"
    if v <= 35:  return "🙂 보통"
    if v <= 75:  return "😷 나쁨"
    return "🚨 매우나쁨"

# ───────────────────────────────────────
# 1. 기상청 단기예보 + 에어코리아 미세먼지
# ───────────────────────────────────────
def get_weather():
    print("  날씨 수집 중 (기상청 API)...")
    import urllib.parse

    kst  = datetime.timezone(datetime.timedelta(hours=9))
    now  = datetime.datetime.now(kst)
    # base_time: 02,05,08,11,14,17,20,23시 중 가장 최근 (발표 후 10분 뒤 제공)
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    cur_hour = now.hour
    # 07시 실행 기준 → 05시 발표 사용
    base_h = max([h for h in base_hours if h <= max(cur_hour - 0, 2)], default=2)
    base_date = now.strftime("%Y%m%d")
    base_time = f"{base_h:02d}00"

    # ── 에어코리아 미세먼지 (전국 한 번에) ──
    air_map = {}
    try:
        import urllib.parse as _up
        airkorea_key = _up.unquote(AIRKOREA_API_KEY)
        # 전국 측정소 실시간 목록 한 번에 조회
        ar = requests.get(
            "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
            params={
                "serviceKey": airkorea_key,
                "returnType": "json",
                "numOfRows":  500,
                "pageNo":     1,
                "sidoName":   "전국",
                "ver":        "1.0",
            },
            timeout=15
        )
        print(f"    에어코리아 상태: {ar.status_code}")
        ar = ar.json()
        for item in ar.get("response", {}).get("body", {}).get("items", []):
            stn = item.get("stationName", "")
            try:
                pm10 = int(float(item.get("pm10Value") or 0))
                pm25 = int(float(item.get("pm25Value") or 0))
            except:
                pm10, pm25 = 0, 0
            air_map[stn] = {"pm10": pm10, "pm25": pm25}
        print(f"    → 에어코리아 {len(air_map)}개 측정소")
    except Exception as e:
        print(f"  ⚠️ 에어코리아 오류: {e}")

    # ── 기상청 단기예보 ──
    import urllib.parse as _up
    kma_key = _up.unquote(KMA_API_KEY)
    cities_data = []
    for city in CITIES:
        try:
            r = requests.get(
                "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
                params={
                    "serviceKey": kma_key,
                    "pageNo":     1,
                    "numOfRows":  1000,
                    "dataType":   "JSON",
                    "base_date":  base_date,
                    "base_time":  base_time,
                    "nx":         city["nx"],
                    "ny":         city["ny"],
                },
                timeout=15
            ).json()
            items = r.get("response", {}).get("body", {}).get("items", {}).get("item", [])

            # 오늘 최고/최저 기온, 하늘 상태 파싱
            today = now.strftime("%Y%m%d")
            tmx, tmn = None, None
            sky_val, pty_val = "1", "0"
            tmp_vals = []  # TMX/TMN 없을 때 TMP로 대체
            for it in items:
                if it["fcstDate"] != today:
                    continue
                cat = it["category"]
                val = it["fcstValue"]
                if cat == "TMX": tmx = float(val)
                if cat == "TMN": tmn = float(val)
                if cat == "TMP":
                    try: tmp_vals.append(float(val))
                    except: pass
                if it["fcstTime"] == "0900":
                    if cat == "SKY": sky_val = val
                    if cat == "PTY": pty_val = val

            # TMX/TMN 없으면 TMP 시간별 최고/최저로 대체
            if tmx is None and tmp_vals: tmx = max(tmp_vals)
            if tmn is None and tmp_vals: tmn = min(tmp_vals)

            icon = kma_icon(sky_val, pty_val)
            high = f"{round(tmx)}°" if tmx is not None else "—"
            low  = f"{round(tmn)}°" if tmn is not None else "—"

            # 미세먼지
            stn_data = air_map.get(city["air_station"], {"pm10": 0, "pm25": 0})
            pm10 = stn_data["pm10"]
            pm25 = stn_data["pm25"]

            cities_data.append({
                "name": city["name"],
                "icon": icon,
                "high": high,
                "low":  low,
                "pm10": pm10,
                "pm25": pm25,
                "pm10_grade": pm10_grade(pm10),
                "pm25_grade": pm25_grade(pm25),
            })
        except Exception as e:
            print(f"  ⚠️ {city['name']} 오류: {e}")

    # ── 서울 주간 예보 ──
    weekly = []
    try:
        seoul = CITIES[0]
        r = requests.get(
            "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst",
            params={
                "serviceKey": kma_key,
                "pageNo":     1,
                "numOfRows":  2000,
                "dataType":   "JSON",
                "base_date":  base_date,
                "base_time":  base_time,
                "nx":         seoul["nx"],
                "ny":         seoul["ny"],
            },
            timeout=15
        ).json()
        items = r.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        day_map = {}
        for it in items:
            d   = it["fcstDate"]
            c   = it["category"]
            v   = it["fcstValue"]
            if d not in day_map:
                dt = datetime.datetime.strptime(d, "%Y%m%d")
                day_map[d] = {
                    "day":  f"{dt.strftime('%m/%d')}({DAYS_KO[dt.weekday()]})",
                    "sky":  "1", "pty": "0",
                    "high": None, "low": None, "tmp": []
                }
            if c == "TMX":
                try: day_map[d]["high"] = float(v)
                except: pass
            if c == "TMN":
                try: day_map[d]["low"] = float(v)
                except: pass
            if c == "TMP":
                try: day_map[d]["tmp"].append(float(v))
                except: pass
            if it["fcstTime"] == "1200":
                if c == "SKY": day_map[d]["sky"] = v
                if c == "PTY": day_map[d]["pty"] = v

        for k in sorted(day_map.keys())[:7]:
            v = day_map[k]
            # TMX/TMN 없으면 TMP 시간별 최고/최저로 대체
            high = v["high"] if v["high"] is not None else (max(v["tmp"]) if v["tmp"] else None)
            low  = v["low"]  if v["low"]  is not None else (min(v["tmp"]) if v["tmp"] else None)
            weekly.append({
                "day":  v["day"],
                "icon": kma_icon(v["sky"], v["pty"]),
                "high": f"{round(high)}°" if high is not None else "—",
                "low":  f"{round(low)}°"  if low  is not None else "—",
            })
    except Exception as e:
        print(f"  ⚠️ 주간예보 오류: {e}")

    # 서울 요약
    overview = f"서울 {cities_data[0]['low']}~{cities_data[0]['high']}" if cities_data else "날씨 준비 중"
    seoul_pm = {
        "pm10":       cities_data[0].get("pm10",  0) if cities_data else 0,
        "pm25":       cities_data[0].get("pm25",  0) if cities_data else 0,
        "pm10_grade": cities_data[0].get("pm10_grade", "") if cities_data else "",
        "pm25_grade": cities_data[0].get("pm25_grade", "") if cities_data else "",
    }
    print(f"  → 도시 {len(cities_data)}개, 주간예보 {len(weekly)}일")
    return {"overview": overview, "detail": "기상청 제공", "cities": cities_data, "weekly": weekly, "seoul_pm": seoul_pm}


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
    import datetime as _dt, os as _os
    kst   = _dt.timezone(_dt.timedelta(hours=9))
    today = _dt.datetime.now(kst)

    # 갱신 여부 판단: 매달 1일 OR 강제 갱신 플래그
    force_refresh = _os.environ.get("FORCE_YT_REFRESH", "").lower() == "true"
    is_refresh_day = (today.day == 1) or force_refresh

    # 인덱스 계산: 1일=0, 2일=1, ... 말일까지
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    idx = today.day - 1  # 1일=0, 2일=1, ...

    CATEGORIES = [
        ("gecko",  ["크레스티드게코 shorts", "도마뱀 귀여운 shorts", "파충류 shorts"]),
        ("animal", ["귀여운 동물 shorts", "동물 웃긴 shorts", "반려동물 귀여운 shorts"]),
        ("funny",  ["웃긴 순간 shorts", "개그 shorts", "반전 웃긴 shorts", "한국 인기 shorts"]),
    ]
    EXCLUDE_WORDS = ["동요", "어린이", "kids", "유아", "아기", "nursery",
                     "children", "동화", "뽀로로", "핑크퐁", "baby shark"]

    # ── 매달 1일 또는 강제 갱신: YouTube API로 목록 수집 ──
    if is_refresh_day and YOUTUBE_API_KEY:
        reason = "강제 갱신" if force_refresh else "매달 갱신일"
        print(f"  ▶ {reason}! YouTube API로 영상 목록 수집 중...")
        lines = [f"# 갱신일: {today.strftime('%Y-%m-%d')}\n"]
        for cat_key, queries in CATEGORIES:
            lines.append(f"# CATEGORY: {cat_key}\n")
            fetched = []
            seen = set()
            for query in queries:  # 부족하면 대체 쿼리로 이어서 수집
                if len(fetched) >= 31:
                    break
                page_token = ""
                while len(fetched) < 31:
                    params = {
                        "part": "snippet",
                        "q": query + " -동요 -어린이 -kids -유아",
                        "type": "video", "videoDuration": "short",
                        "regionCode": "KR", "relevanceLanguage": "ko",
                        "order": "viewCount", "safeSearch": "strict",
                        "maxResults": 50, "key": YOUTUBE_API_KEY,
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    sr = requests.get("https://www.googleapis.com/youtube/v3/search",
                                      params=params, timeout=15).json()
                    for item in sr.get("items", []):
                        vid   = item["id"].get("videoId", "")
                        title = item["snippet"]["title"].replace("|", "｜")
                        if not vid or vid in seen:
                            continue
                        if any(w.lower() in title.lower() for w in EXCLUDE_WORDS):
                            continue
                        dr = requests.get("https://www.googleapis.com/youtube/v3/videos",
                                          params={"part": "contentDetails,status", "id": vid,
                                                  "key": YOUTUBE_API_KEY}, timeout=10).json()
                        items_d = dr.get("items", [])
                        if not items_d:
                            continue
                        vd = items_d[0]
                        st = vd.get("status", {})
                        cd = vd.get("contentDetails", {})
                        # 임베드 불가 / 비공개 / 연령제한 제외
                        if not st.get("embeddable", True):
                            continue
                        if st.get("privacyStatus", "public") != "public":
                            continue
                        if cd.get("contentRating", {}):
                            continue
                        if _parse_duration(cd["duration"]) <= 60:
                            seen.add(vid)
                            fetched.append(f"https://www.youtube.com/shorts/{vid} | {title}\n")
                        if len(fetched) >= 31:
                            break
                    page_token = sr.get("nextPageToken", "")
                    if not page_token:
                        break
            # funny 카테고리가 31개 미달이면 전체 인기 Shorts로 보충
            if cat_key == "funny" and len(fetched) < 31:
                print(f"    → funny 부족({len(fetched)}개), 전체 인기 Shorts로 보충...")
                pr = requests.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet,contentDetails,status", "chart": "mostPopular",
                            "regionCode": "KR", "maxResults": 50,
                            "key": YOUTUBE_API_KEY},
                    timeout=15
                ).json()
                for item in pr.get("items", []):
                    vid   = item["id"]
                    title = item["snippet"]["title"].replace("|", "｜")
                    if not vid or vid in seen:
                        continue
                    if any(w.lower() in title.lower() for w in EXCLUDE_WORDS):
                        continue
                    st = item.get("status", {})
                    cd = item.get("contentDetails", {})
                    if not st.get("embeddable", True):
                        continue
                    if st.get("privacyStatus", "public") != "public":
                        continue
                    if cd.get("contentRating", {}):
                        continue
                    if _parse_duration(cd["duration"]) <= 60:
                        seen.add(vid)
                        fetched.append(f"https://www.youtube.com/shorts/{vid} | {title}\n")
                    if len(fetched) >= 31:
                        break
            lines.extend(fetched)
            print(f"    → {cat_key}: {len(fetched)}개 수집")
        with open("video_contents.txt", "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("  ✅ video_contents.txt 갱신 완료")

    # ── 매일: 파일에서 인덱스 해당 영상 읽기 ──
    videos = []
    try:
        cats = {}
        cur_cat = None
        with open("video_contents.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("# CATEGORY:"):
                    cur_cat = line.split(":", 1)[1].strip()
                    cats[cur_cat] = []
                elif not line.startswith("#") and cur_cat:
                    parts = [p.strip() for p in line.split("|")]
                    url   = parts[0]
                    title = parts[1] if len(parts) > 1 else "오늘의 영상"
                    import re as _re
                    m = _re.search(r"shorts/([A-Za-z0-9_-]+)", url)
                    if m:
                        cats[cur_cat].append({
                            "title": title,
                            "embed": f"https://www.youtube.com/embed/{m.group(1)}",
                            "url":   url,
                        })
        for cat_key, _ in CATEGORIES:
            pool = cats.get(cat_key, [])
            if pool:
                videos.append(pool[idx % len(pool)])
        print(f"  → 영상 {len(videos)}개 로드 (인덱스: {idx})")
    except FileNotFoundError:
        print("  ⚠️ video_contents.txt 없음 — 영상 섹션 생략")
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
    tools_section = '''<!-- TOOLS -->
<div class="sec-hd"><span class="sec-hd-label">Tools</span><div class="sec-hd-line"></div><span class="sec-tag tag-weather">🛠 유용한 툴</span></div>
<div class="tools-row">
  <a class="tool-link-card" href="https://크레오늘.com/tools/hatching_calculator" target="_blank">
    <span class="tool-link-icon">🥚</span>
    <span class="tool-link-name">해칭 계산기</span>
    <span class="tool-link-arrow">›</span>
  </a>
  <a class="tool-link-card" href="https://크레오늘.com/tools/morph_calculator" target="_blank">
    <span class="tool-link-icon">🧬</span>
    <span class="tool-link-name">모프 계산기</span>
    <span class="tool-link-arrow">›</span>
  </a>
  <a class="tool-link-card" href="https://크레오늘.com/tools/tray_manager" target="_blank">
    <span class="tool-link-icon">📦</span>
    <span class="tool-link-name">트레이 관리</span>
    <span class="tool-link-arrow">›</span>
  </a>
</div>'''
    if ads:
        tabs = ""
        panels = ""
        for i, ad in enumerate(ads):
            active = "active" if i == 0 else ""
            tabs += f'<div class="adtab {active}" onclick="showAd({i})">{i+1}</div>'
            img_html = f'<img src="{ad["image"]}" alt="">' if ad["image"] else ""
            link_html = f'<a class="adpanel-link" href="{ad["url"]}" target="_blank">🔗 {ad["url"]}</a>' if ad["url"] and ad["url"] != "#" else ""
            # 첫 줄 = 제목, 나머지 = 본문
            lines = ad["text"].split("\n", 1)
            title_html = f'<div class="adpanel-title">{lines[0]}</div>'
            body_html  = f'<div class="adpanel-text">{lines[1]}</div>' if len(lines) > 1 else ""
            panels += f'''<div class="adpanel {active}">
  <a href="{ad['url']}" target="_blank">{img_html}</a>
  {title_html}
  {body_html}
  {link_html}
</div>'''

        ads_section = f'''<!-- ADS -->
<div class="sec-hd"><span class="sec-hd-label">Community</span><div class="sec-hd-line"></div><span class="sec-tag tag-yt">📌 커뮤니티 소식</span></div>
<div class="ads-wrap">
  <div class="ads-nav">
    <div class="ads-arrow" id="ad-prev" onclick="moveAd(-1)">&#8249;</div>
    <div class="ads-tabs">{tabs}</div>
    <div class="ads-arrow" id="ad-next" onclick="moveAd(1)">&#8250;</div>
  </div>
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
    yt_count = len(videos)
    for i, v in enumerate(videos):
        active = "active" if i == 0 else ""
        yt_tabs   += f'<div class="yt-dot {active}" onclick="showVid({i})"></div>'
        yt_panels += f"""<div class="mpanel {active}" id="vpanel-{i}">
          <iframe src="{v['embed']}" frameborder="0" allowfullscreen
            style="width:100%;aspect-ratio:9/16;border-radius:12px;display:block;"></iframe>
          <a class="yt-link" href="{v['url']}" target="_blank">▶ {v['title']}</a>
        </div>"""

    yt_section = ""
    if videos:
        yt_section = f"""
<!-- YOUTUBE -->
<div class="sec-hd"><span class="sec-hd-label">YouTube</span><div class="sec-hd-line"></div><span class="sec-tag tag-yt">🎬 오늘의 Shorts</span></div>
<div class="yt-nav">
  <button class="yt-arrow-btn" id="yt-prev" onclick="moveVid(-1)">&#8249;</button>
  <div class="yt-counter"><span id="yt-cur">1</span> / {yt_count}</div>
  <div class="yt-dots">{yt_tabs}</div>
  <button class="yt-arrow-btn on" id="yt-next" onclick="moveVid(1)">&#8250;</button>
</div>
<div class="yt-panels-wrap">
{yt_panels}
</div>"""

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
.ads-nav{{display:flex;align-items:center;gap:8px;margin-bottom:10px}}
.ads-tabs{{display:flex;gap:6px;flex:1;overflow-x:auto;scrollbar-width:none}}
.ads-tabs::-webkit-scrollbar{{display:none}}
.ads-arrow{{width:28px;height:28px;border-radius:50%;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.07);color:rgba(255,255,255,.3);font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s;user-select:none}}
.ads-arrow.on{{color:#c8f0a0;border-color:#3d7a3a;background:rgba(61,122,58,.2)}}
.ads-arrow.on:hover{{background:rgba(61,122,58,.4)}}
.adtab{{flex-shrink:0;padding:5px 12px;border-radius:20px;font-size:11px;background:rgba(255,255,255,.07);color:rgba(255,255,255,.5);cursor:pointer;border:1px solid rgba(255,255,255,.1);transition:.2s}}
.adtab.active{{background:#3d7a3a;color:#c8f0a0;border-color:#3d7a3a}}
.adpanel{{display:none;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;overflow:hidden}}
.adpanel.active{{display:block}}
.adpanel a{{display:block;text-decoration:none;color:inherit}}
.adpanel img{{width:100%;display:block;object-fit:contain}}
.adpanel-title{{padding:12px 14px 4px;font-size:15px;font-weight:900;color:#fff;line-height:1.4}}
.adpanel-text{{padding:0 14px 10px;font-size:12px;color:rgba(255,255,255,.7);line-height:1.8;white-space:pre-line}}
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
.yt-nav{{display:flex;align-items:center;gap:10px;padding:0 16px 12px}}
.yt-arrow-btn{{width:36px;height:36px;border-radius:50%;border:none;background:rgba(255,166,87,.15);color:rgba(255,255,255,.3);font-size:20px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s;line-height:1}}
.yt-arrow-btn.on{{background:rgba(255,166,87,.25);color:#ffa657;box-shadow:0 0 0 1px rgba(255,166,87,.4)}}
.yt-arrow-btn.on:hover{{background:rgba(255,166,87,.4)}}
.yt-counter{{font-family:'DM Mono',monospace;font-size:13px;color:rgba(255,255,255,.5);flex-shrink:0;min-width:36px;text-align:center}}
.yt-dots{{display:flex;gap:6px;flex:1;justify-content:center}}
.yt-dot{{width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.1);cursor:pointer;transition:.2s;font-size:11px;font-family:'DM Mono',monospace;color:rgba(255,255,255,.4);display:flex;align-items:center;justify-content:center}}
.yt-dot.active{{background:rgba(255,166,87,.25);border-color:#ffa657;color:#ffa657}}
.yt-panels-wrap{{padding:0 16px 16px}}
.mpanel{{display:none}}
.mpanel.active{{display:block}}
.yt-link{{display:block;margin-top:8px;font-size:11px;color:#58a6ff;text-decoration:none;line-height:1.5}}
.tools-row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;padding:0 16px 16px}}
.tool-link-card{{display:flex;align-items:center;gap:8px;background:#0d1117;border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:12px 14px;text-decoration:none;color:inherit;transition:all .2s}}
.tool-link-card:hover{{border-color:rgba(88,166,255,.3);background:rgba(88,166,255,.05)}}
.tool-link-icon{{font-size:20px;flex-shrink:0}}
.tool-link-name{{font-size:12px;font-weight:700;color:#e6edf3;flex:1}}
.tool-link-arrow{{font-size:16px;color:rgba(255,255,255,.25);transition:transform .2s;animation:nudge 2s ease-in-out infinite}}
@keyframes nudge{{0%,60%,100%{{transform:translateX(0)}}70%{{transform:translateX(4px)}}80%{{transform:translateX(0)}}90%{{transform:translateX(4px)}}}}
.tool-link-card:hover .tool-link-arrow{{animation:none;transform:translateX(3px);color:#58a6ff}}
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

{tools_section}

<!-- WEATHER -->
<div class="sec-hd"><span class="sec-hd-label">Weather</span><div class="sec-hd-line"></div><span class="sec-tag tag-weather">전국 날씨</span></div>
<div class="fortune-img">
  <img src="images/today_weather.jpg?v={date_info['date_str'].replace('-','')}" alt="오늘의 날씨"
       onerror="this.parentElement.innerHTML='<div class=\'fortune-empty\'>☀️ 오늘의 날씨 이미지 준비 중<br><small>images/today_weather.jpg 업로드 해주세요</small></div>'">
</div>
<div class="fortune-img">
  <img src="images/today_finedust.jpg?v={date_info['date_str'].replace('-','')}" alt="오늘의 미세먼지"
       onerror="this.parentElement.innerHTML='<div class=\'fortune-empty\'>🌫 오늘의 미세먼지 이미지 준비 중<br><small>images/today_finedust.jpg 업로드 해주세요</small></div>'">
</div>

{yt_section}

{ads_section}

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

<!-- FOOTER -->
<div class="footer">
  🦎 Crested Gecko Community · {date_info['date_ko']}<br>
  날씨 제공: 기상청 · 미세먼지: 에어코리아 · 뉴스 제공: 네이버 검색
  <div id="admin-counter" style="display:none;margin-top:8px;font-size:11px;color:rgba(255,255,255,.5)">
    👁 누적 조회수: <span id="view-count">...</span>
  </div>
  <div class="footer-credit">
    <img src="images/kkug_cre.png" alt="kkug.cre">
    <span>Designed by @kkug.cre</span>
  </div>
</div>

</div>
<script>
function showVid(i) {{
  const dots   = document.querySelectorAll('.yt-dot');
  const panels = document.querySelectorAll('.mpanel');
  const total  = dots.length;
  if (i < 0 || i >= total) return;
  dots.forEach((d,idx)   => d.classList.toggle('active', idx===i));
  panels.forEach((p,idx) => p.classList.toggle('active', idx===i));
  // 카운터 업데이트
  const cur = document.getElementById('yt-cur');
  if (cur) cur.textContent = i + 1;
  // 화살표 활성화
  const prev = document.getElementById('yt-prev');
  const next = document.getElementById('yt-next');
  if (prev) prev.classList.toggle('on', i > 0);
  if (next) next.classList.toggle('on', i < total - 1);
}}
function moveVid(dir) {{
  const dots = document.querySelectorAll('.yt-dot');
  let cur = 0;
  dots.forEach((d,i) => {{ if (d.classList.contains('active')) cur = i; }});
  showVid(cur + dir);
}}
// 초기 dot 번호 표시
(function() {{
  const dots = document.querySelectorAll('.yt-dot');
  dots.forEach((d,i) => d.textContent = i + 1);
  const next = document.getElementById('yt-next');
  if (next && dots.length > 1) next.classList.add('on');
}})();
function showAd(i) {{
  const tabs   = document.querySelectorAll('.adtab');
  const panels = document.querySelectorAll('.adpanel');
  const total  = tabs.length;
  if (i < 0 || i >= total) return;
  tabs.forEach((t,idx)   => t.classList.toggle('active', idx===i));
  panels.forEach((p,idx) => p.classList.toggle('active', idx===i));
  const prev = document.getElementById('ad-prev');
  const next = document.getElementById('ad-next');
  if (prev) prev.classList.toggle('on', i > 0);
  if (next) next.classList.toggle('on', i < total - 1);
}}
function moveAd(dir) {{
  const tabs = document.querySelectorAll('.adtab');
  let cur = 0;
  tabs.forEach((t,i) => {{ if (t.classList.contains('active')) cur = i; }});
  showAd(cur + dir);
}}
(function() {{
  const tabs = document.querySelectorAll('.adtab');
  const next = document.getElementById('ad-next');
  if (next && tabs.length > 1) next.classList.add('on');
}})();
(function() {{
  const params = new URLSearchParams(location.search);
  const hash   = location.hash;
  // 날짜 표시
  const d = params.get('d');
  if (d && d.length === 8) {{
    const el = document.querySelector('.hd-date-big');
    if (el) el.textContent = d.slice(6,8);
  }}
  // 조회수 카운터 (항상 카운트, 관리자만 표시)
  fetch('https://api.counterapi.dev/v1/cretoday-briefing/views/up')
    .then(r => r.json())
    .then(data => {{
      if (hash === '#admin') {{
        document.getElementById('view-count').textContent = data.count.toLocaleString();
        document.getElementById('admin-counter').style.display = 'block';
      }}
    }})
    .catch(() => {{}});
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
    # video_contents.txt 가 있으면 함께 커밋
    import os as _os
    if _os.path.exists("video_contents.txt"):
        subprocess.run(["git", "add", "video_contents.txt"], check=True)
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
