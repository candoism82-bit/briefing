#!/usr/bin/env python3
"""🦎 Crested Gecko Community - Daily Briefing Auto-Generator"""
import os, re, json, time, datetime, subprocess
from googleapiclient.discovery import build
import anthropic

YOUTUBE_API_KEY   = os.environ["YOUTUBE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# ───── 프로모 배너 (하드코딩) ─────
PROMO_CSS = """
.promo-banner{background:linear-gradient(160deg,#0a1f08,#1a3a15,#0e2a0a);border-bottom:3px solid #3d7a3a;position:relative;overflow:hidden}
.promo-inner{padding:22px 24px 20px;position:relative;z-index:1}
.promo-badge-row{display:flex;align-items:center;gap:8px;margin-bottom:14px}
.promo-badge{background:#3d7a3a;color:#c8f0a0;font-size:9px;letter-spacing:.12em;text-transform:uppercase;padding:3px 10px;border-radius:20px}
.promo-badge-line{flex:1;height:1px;background:rgba(255,255,255,.08)}
.promo-copy{text-align:center;margin-bottom:18px}
.promo-heart{font-size:28px;margin-bottom:8px;display:block;animation:heartbeat 1.8s ease infinite}
@keyframes heartbeat{0%,100%{transform:scale(1)}30%{transform:scale(1.18)}70%{transform:scale(1.1)}}
.promo-main-text{font-size:18px;font-weight:900;color:#fff;line-height:1.55;margin-bottom:6px}
.promo-main-text em{color:#7ae050;font-style:normal}
.promo-sub-text{font-size:13px;color:rgba(255,255,255,.65);line-height:1.7}
.promo-sub-text strong{color:#a8e060}
.promo-org-box{background:rgba(106,173,69,.12);border:1px solid rgba(106,173,69,.35);border-radius:8px;padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.promo-org-name{font-size:16px;font-weight:900;color:#fff;display:flex;align-items:center;gap:6px;margin-bottom:4px}
.promo-org-url{font-size:11px;color:#6aad45;text-decoration:none;border-bottom:1px solid rgba(106,173,69,.4)}
.promo-qr-hint{text-align:center;flex-shrink:0}
.promo-qr-emoji{font-size:36px}
.promo-qr-label{font-size:9px;color:rgba(255,255,255,.3);display:block}
.promo-img-wrap{border-radius:8px;overflow:hidden;border:1px solid rgba(106,173,69,.25)}
.promo-img-wrap img{width:100%;display:block}
"""

PROMO_HTML = """<!-- LITTLE LIVES -->
<div class="promo-banner"><div class="promo-inner">
  <div class="promo-badge-row"><span class="promo-badge">🌿 함께해요</span><div class="promo-badge-line"></div><span class="promo-badge">파충류 권익 보호</span></div>
  <div class="promo-copy">
    <span class="promo-heart">♥️</span>
    <div class="promo-main-text">생명을 소중히 여기신다면<br><em>함께해 주시고 힘을 실어주세요</em></div>
    <div class="promo-sub-text"><strong>집사님들이 관심을 가져주셔야!</strong><br>더 좋은 환경에서 키우실 수 있습니다! 🦎</div>
  </div>
  <div class="promo-org-box">
    <div><div class="promo-org-name">사단법인 작은생명공존연합 <span>‼️</span></div>
    <a class="promo-org-url" href="https://www.littlelives.or.kr/" target="_blank">🔗 www.littlelives.or.kr</a></div>
    <div class="promo-qr-hint"><div class="promo-qr-emoji">🐊</div><span class="promo-qr-label">Little Lives</span></div>
  </div>
  <div class="promo-img-wrap"><img src="images/littlelives.png" alt="작은생명공존연합"></div>
</div></div>"""


def get_youtube_shorts():
    try:
        yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        week_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = yt.search().list(q="crested gecko", part="snippet", type="video",
                               videoDuration="short", order="viewCount",
                               publishedAfter=week_ago, maxResults=3).execute()
        if not res.get("items"):
            res = yt.search().list(q="crested gecko cute", part="snippet", type="video",
                                   videoDuration="short", order="viewCount", maxResults=3).execute()
        items = res.get("items", [])
        if not items:
            return None
        vid = items[0]["id"]["videoId"]
        return {"title": items[0]["snippet"]["title"],
                "channel": items[0]["snippet"]["channelTitle"],
                "embed": f"https://www.youtube.com/embed/{vid}?autoplay=0",
                "url": f"https://www.youtube.com/shorts/{vid}"}
    except Exception as e:
        print(f"  ⚠️ YouTube 오류: {e}")
        return None


def call_with_retry(fn, max_retries=3):
    """RateLimitError 시 자동 대기 후 재시도"""
    import anthropic as _ant
    for attempt in range(max_retries):
        try:
            return fn()
        except _ant.RateLimitError as e:
            wait = 65 * (attempt + 1)
            print(f"  ⏳ Rate limit — {wait}초 대기 후 재시도 ({attempt+1}/{max_retries})...")
            time.sleep(wait)
    raise RuntimeError("Rate limit 재시도 초과")


def collect_data(date_info):
    """웹 검색 2회로 데이터 수집 — 날씨/뉴스 + 운세/별자리/밈"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ── 1-A: 날씨 + 뉴스 ──
    prompt_a = f"""오늘 {date_info['date_ko']} 한국 데이터를 웹 검색해서 JSON으로만 반환. 설명 없이 JSON만.
키:
- weather: overview(str), detail(str), cities(배열6, name/high/low/icon), weekly(배열7, day/icon/high/low)
- economy_news: 배열4, title/summary/url/source
- politics_news: 배열4, title/summary/url/source"""

    print("  [A] 날씨·뉴스 수집 중...")
    res_a = call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-6", max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt_a}]
    ))
    raw_a = "".join(b.text for b in res_a.content if hasattr(b, "text"))
    raw_a = re.sub(r"```json\s*|```", "", raw_a).strip()
    sa, ea = raw_a.find("{"), raw_a.rfind("}") + 1
    try:
        data_a = json.loads(raw_a[sa:ea])
    except json.JSONDecodeError:
        from json_repair import repair_json
        data_a = json.loads(repair_json(raw_a[sa:ea]))
    print(f"  [A] 완료 — 뉴스 {len(data_a.get('economy_news',[]))+len(data_a.get('politics_news',[]))}건")

    # ── 1-B: 띠별 운세 ──
    prompt_b = f"""오늘 {date_info['date_ko']} 띠별 운세를 웹 검색해서 JSON으로만 반환. 설명 없이 JSON만.
키:
- zodiac: 배열12, 각각 sign/emoji/summary/years(배열5, year/text)
  쥐🐭(60/72/84/96/08), 소🐮(61/73/85/97/09), 호랑이🐯(62/74/86/98/10), 토끼🐰(63/75/87/99/11),
  용🐲(64/76/88/00/12), 뱀🐍(65/77/89/01/13), 말🐴(66/78/90/02/14), 양🐑(67/79/91/03/15),
  원숭이🐵(68/80/92/04/16), 닭🐔(69/81/93/05/17), 개🐶(70/82/94/06/18), 돼지🐷(71/83/95/07/19)"""

    print("  [B] 띠별 운세 수집 중...")
    res_b = call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-6", max_tokens=5000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt_b}]
    ))
    raw_b = "".join(b.text for b in res_b.content if hasattr(b, "text"))
    raw_b = re.sub(r"```json\s*|```", "", raw_b).strip()
    sb, eb = raw_b.find("{"), raw_b.rfind("}") + 1
    try:
        data_b = json.loads(raw_b[sb:eb])
    except json.JSONDecodeError:
        from json_repair import repair_json
        data_b = json.loads(repair_json(raw_b[sb:eb]))
    print(f"  [B] 완료 — 운세 {len(data_b.get('zodiac',[]))}띠")

    # ── 1-C: 별자리 + 밈 ──
    prompt_c = f"""오늘 {date_info['date_ko']} 별자리 운세를 웹 검색해서 JSON으로만 반환. 설명 없이 JSON만.
키:
- horoscope: 배열12, 각각 sign/emoji/date/text
  양자리♈(3.21~4.19), 황소자리♉(4.20~5.20), 쌍둥이자리♊(5.21~6.21), 게자리♋(6.22~7.22),
  사자자리♌(7.23~8.22), 처녀자리♍(8.23~9.22), 천칭자리♎(9.23~10.23), 전갈자리♏(10.24~11.21),
  사수자리♐(11.22~12.21), 염소자리♑(12.22~1.19), 물병자리♒(1.20~2.18), 물고기자리♓(2.19~3.20)
- meme_drips: 오늘 뉴스 키워드 기반 재미있는 드립 3개 배열"""

    print("  [C] 별자리·밈 수집 중...")
    res_c = call_with_retry(lambda: client.messages.create(
        model="claude-sonnet-4-6", max_tokens=3000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt_c}]
    ))
    raw_c = "".join(b.text for b in res_c.content if hasattr(b, "text"))
    raw_c = re.sub(r"```json\s*|```", "", raw_c).strip()
    sc, ec = raw_c.find("{"), raw_c.rfind("}") + 1
    try:
        data_c = json.loads(raw_c[sc:ec])
    except json.JSONDecodeError:
        from json_repair import repair_json
        data_c = json.loads(repair_json(raw_c[sc:ec]))
    print(f"  [C] 완료 — 별자리 {len(data_c.get('horoscope',[]))}개, 밈 {len(data_c.get('meme_drips',[]))}개")

    return {**data_a, **data_b, **data_c}


def build_html(data, youtube, date_info):
    """Claude API 없이 Python으로 직접 HTML 조립 — 절대 잘리지 않음"""

    w   = data.get("weather", {})
    eco = data.get("economy_news", [])
    pol = data.get("politics_news", [])
    zod = data.get("zodiac", [])
    hor = data.get("horoscope", [])
    drips = data.get("meme_drips", ["드립 준비 중...","드립 준비 중...","드립 준비 중..."])

    # ── 날씨 도시 ──
    cities_html = ""
    for c in w.get("cities", []):
        cities_html += f"""
        <div class="city-card">
          <div class="city-name">{c.get('name','')}</div>
          <div class="city-high">{c.get('high','')}</div>
          <div class="city-low">{c.get('low','')}</div>
          <div class="city-icon">{c.get('icon','🌤')}</div>
        </div>"""

    # ── 주간 예보 ──
    weekly_html = ""
    for d in w.get("weekly", []):
        weekly_html += f"""
        <div class="week-day">
          <div class="wd-label">{d.get('day','')}</div>
          <div class="wd-icon">{d.get('icon','')}</div>
          <div class="wd-high">{d.get('high','')}</div>
          <div class="wd-low">{d.get('low','')}</div>
        </div>"""

    # ── 뉴스 ──
    def news_items(items):
        html = ""
        for i, n in enumerate(items, 1):
            html += f"""
        <div class="news-item">
          <span class="news-num">0{i}</span>
          <div class="news-body">
            <a class="news-title" href="{n.get('url','#')}" target="_blank">{n.get('title','')}</a>
            <div class="news-summary">{n.get('summary','')}</div>
            <div class="news-source">▸ {n.get('source','')}</div>
          </div>
        </div>"""
        return html

    # ── 띠별 운세 탭 ──
    zod_tabs = ""
    zod_panels = ""
    for i, z in enumerate(zod):
        active = "active" if i == 0 else ""
        zod_tabs += f'<button class="ztab {active}" onclick="showZod({i})">{z.get("emoji","")}<br><span>{z.get("sign","")}</span></button>'
        years_html = ""
        for y in z.get("years", []):
            years_html += f'<div class="zy-item"><span class="zy-year">{y.get("year","")}</span><span class="zy-text">{y.get("text","")}</span></div>'
        zod_panels += f"""
        <div class="zpanel {'active' if i==0 else ''}" id="zpanel-{i}">
          <div class="zpanel-summary">{z.get('summary','')}</div>
          {years_html}
        </div>"""

    # ── 별자리 ──
    hor_html = ""
    for h in hor:
        hor_html += f"""
        <div class="hor-card">
          <div class="hor-emoji">{h.get('emoji','')}</div>
          <div class="hor-sign">{h.get('sign','')}</div>
          <div class="hor-date">{h.get('date','')}</div>
          <div class="hor-text">{h.get('text','')}</div>
        </div>"""

    # ── 밈 존 ──
    drip_items = "".join(f'<div class="drip-item">💬 {d}</div>' for d in drips)

    # ── 유튜브 탭 ──
    yt_tab = ""
    yt_panel = ""
    if youtube:
        yt_tab = f'<button class="mtab active" onclick="showMeme(\'shorts\')">📺 Shorts</button>'
        yt_panel = f"""
        <div class="mpanel active" id="mpanel-shorts">
          <div class="yt-wrap">
            <iframe src="{youtube['embed']}" frameborder="0" allowfullscreen style="width:100%;aspect-ratio:9/16;border-radius:8px;"></iframe>
            <a class="yt-link" href="{youtube['url']}" target="_blank">▶ YouTube에서 보기 — {youtube['title']}</a>
          </div>
        </div>"""
        pass
    else:
        pass

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>🦎 크레스티드 게코 커뮤니티 아침 브리핑 · {date_info['date_ko']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&family=Noto+Serif+KR:wght@700;900&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:'Noto Sans KR',sans-serif;display:flex;justify-content:center;padding:16px}}
.card{{width:100%;max-width:480px;border-radius:16px;overflow:hidden;background:#161b22;box-shadow:0 8px 32px rgba(0,0,0,.5)}}

/* HEADER */
.hd{{background:linear-gradient(135deg,#1a2332,#0d1f35);padding:24px;position:relative;overflow:hidden}}
.hd::before{{content:'🦎';position:absolute;right:-10px;top:-10px;font-size:80px;opacity:.08}}
.hd-eyebrow{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:#58a6ff;text-transform:uppercase;margin-bottom:4px}}
.hd-title{{font-family:'Noto Serif KR',serif;font-size:26px;font-weight:900;color:#fff;display:flex;align-items:center;gap:8px}}
.hd-sub{{font-size:11px;color:rgba(255,255,255,.4);margin-top:4px;letter-spacing:.05em}}
.hd-inner{{display:flex;justify-content:space-between;align-items:flex-start}}
.hd-date-big{{font-family:'DM Mono',monospace;font-size:52px;font-weight:700;color:#58a6ff;line-height:1}}
.hd-date-small{{font-family:'DM Mono',monospace;font-size:10px;color:rgba(255,255,255,.4);text-align:right;letter-spacing:.08em}}

/* PROMO */
.promo-banner{{background:linear-gradient(160deg,#0a1f08,#1a3a15,#0e2a0a);border-bottom:3px solid #3d7a3a;position:relative;overflow:hidden}}
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

/* SECTION HEADER */
.sec-hd{{display:flex;align-items:center;gap:8px;padding:20px 20px 12px}}
.sec-hd-label{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.15em;color:#58a6ff;text-transform:uppercase}}
.sec-hd-line{{flex:1;height:1px;background:rgba(255,255,255,.08)}}
.sec-tag{{font-size:9px;padding:2px 8px;border-radius:10px;letter-spacing:.06em}}
.tag-weather{{background:rgba(88,166,255,.15);color:#58a6ff}}
.tag-eco{{background:rgba(63,185,80,.15);color:#3fb950}}
.tag-pol{{background:rgba(248,81,73,.15);color:#f85149}}
.tag-zod{{background:rgba(210,153,34,.15);color:#d2a61a}}
.tag-hor{{background:rgba(188,140,255,.15);color:#bc8cff}}
.tag-meme{{background:rgba(255,166,87,.15);color:#ffa657}}

/* WEATHER */
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
.weekly{{display:flex;justify-content:space-between;padding:0 16px 20px;gap:4px}}
.week-day{{flex:1;text-align:center;background:#0d1117;border-radius:6px;padding:8px 4px;border:1px solid rgba(255,255,255,.06)}}
.wd-label{{font-size:10px;color:rgba(255,255,255,.5);margin-bottom:4px}}
.wd-icon{{font-size:16px;margin-bottom:4px}}
.wd-high{{font-size:12px;font-weight:700;color:#e6edf3}}
.wd-low{{font-size:10px;color:rgba(255,255,255,.35)}}

/* NEWS */
.news-list{{padding:0 16px 16px;display:flex;flex-direction:column;gap:10px}}
.news-item{{display:flex;gap:10px;background:#0d1117;border-radius:8px;padding:12px;border:1px solid rgba(255,255,255,.06)}}
.news-num{{font-family:'DM Mono',monospace;font-size:11px;color:#58a6ff;flex-shrink:0;padding-top:2px}}
.news-title{{font-size:13px;font-weight:700;color:#e6edf3;text-decoration:none;display:block;margin-bottom:4px;line-height:1.5}}
.news-title:hover{{color:#58a6ff}}
.news-summary{{font-size:11px;color:rgba(255,255,255,.55);line-height:1.6;margin-bottom:4px}}
.news-source{{font-size:10px;color:#3fb950}}

/* ZODIAC */
.ztabs{{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;padding:0 16px 12px}}
.ztab{{background:#0d1117;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:6px 2px;font-size:16px;color:rgba(255,255,255,.5);cursor:pointer;text-align:center;line-height:1.3;transition:.2s}}
.ztab span{{font-size:8px;display:block;margin-top:2px}}
.ztab.active{{background:rgba(210,153,34,.15);border-color:#d2a61a;color:#e6edf3}}
.zpanels{{padding:0 16px 16px}}
.zpanel{{display:none}}
.zpanel.active{{display:block}}
.zpanel-summary{{font-size:12px;color:#d2a61a;margin-bottom:10px;padding:8px 12px;background:rgba(210,153,34,.08);border-radius:6px;border-left:3px solid #d2a61a}}
.zy-item{{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05)}}
.zy-year{{font-family:'DM Mono',monospace;font-size:10px;color:#58a6ff;flex-shrink:0;padding-top:2px;min-width:40px}}
.zy-text{{font-size:12px;color:rgba(255,255,255,.75);line-height:1.6}}

/* HOROSCOPE */
.hor-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:0 16px 16px}}
.hor-card{{background:#0d1117;border-radius:8px;padding:10px;border:1px solid rgba(255,255,255,.06)}}
.hor-emoji{{font-size:20px;margin-bottom:3px}}
.hor-sign{{font-size:11px;font-weight:700;color:#e6edf3;margin-bottom:1px}}
.hor-date{{font-size:9px;color:rgba(255,255,255,.35);margin-bottom:4px}}
.hor-text{{font-size:10px;color:rgba(255,255,255,.6);line-height:1.5}}

/* MEME */
.mtabs{{display:flex;gap:6px;padding:0 16px 12px;flex-wrap:wrap}}
.mtab{{background:#0d1117;border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:5px 12px;font-size:11px;color:rgba(255,255,255,.5);cursor:pointer;transition:.2s}}
.mtab.active{{background:rgba(255,166,87,.15);border-color:#ffa657;color:#ffa657}}
.mpanel{{display:none;padding:0 16px 16px}}
.mpanel.active{{display:block}}
.drip-item{{background:#0d1117;border-radius:8px;padding:12px;margin-bottom:8px;font-size:13px;color:rgba(255,255,255,.75);border:1px solid rgba(255,255,255,.06);line-height:1.6}}
.yt-wrap iframe{{width:100%;aspect-ratio:9/16;border-radius:8px}}
.yt-link{{display:block;margin-top:8px;font-size:11px;color:#58a6ff;text-decoration:none}}

/* FOOTER */
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
      <div class="hd-sub">날씨 · 경제 · 정치 · 운세 · 밈</div>
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
    <div><div class="promo-org-name">사단법인 작은생명공존연합 <span>‼️</span></div>
    <a class="promo-org-url" href="https://www.littlelives.or.kr/" target="_blank">🔗 www.littlelives.or.kr</a></div>
    <div><div class="promo-qr-emoji">🐊</div><span class="promo-qr-label">Little Lives</span></div>
  </div>
  <div class="promo-img-wrap"><img src="images/littlelives.png" alt="작은생명공존연합"></div>
</div></div>

<!-- WEATHER -->
<div class="sec-hd"><span class="sec-hd-label">Weather</span><div class="sec-hd-line"></div><span class="sec-tag tag-weather">전국 날씨</span></div>
<div class="weather-ov">
  <div class="weather-ov-icon">🌤</div>
  <div>
    <div class="weather-ov-title">{w.get('overview','')}</div>
    <div class="weather-ov-sub">{w.get('detail','')}</div>
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

<!-- ZODIAC -->
<div class="sec-hd"><span class="sec-hd-label">Zodiac</span><div class="sec-hd-line"></div><span class="sec-tag tag-zod">띠별 운세</span></div>
<div class="ztabs">{zod_tabs}</div>
<div class="zpanels">{zod_panels}</div>

<!-- HOROSCOPE -->
<div class="sec-hd"><span class="sec-hd-label">Horoscope</span><div class="sec-hd-line"></div><span class="sec-tag tag-hor">별자리 운세</span></div>
<div class="hor-grid">{hor_html}</div>

<!-- MEME -->
<div class="sec-hd"><span class="sec-hd-label">Meme Zone</span><div class="sec-hd-line"></div><span class="sec-tag tag-meme">오늘의 밈</span></div>
<div class="mtabs">
  {yt_tab}
  <button class="mtab {'active' if not youtube else ''}" onclick="showMeme('drip')">💬 드립</button>
</div>
{yt_panel}
<div class="mpanel {'active' if not youtube else ''}" id="mpanel-drip">
  {drip_items}
</div>

<!-- FOOTER -->
<div class="footer">
  🦎 Crested Gecko Community · {date_info['date_ko']}<br>
  매일 아침 자동 생성 · 크레스티드 게코 집사들의 하루 시작
</div>

</div>
<script>
function showZod(i){{
  document.querySelectorAll('.ztab').forEach((t,idx)=>t.classList.toggle('active',idx===i));
  document.querySelectorAll('.zpanel').forEach((p,idx)=>p.classList.toggle('active',idx===i));
}}
function showMeme(id){{
  document.querySelectorAll('.mtab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.mpanel').forEach(p=>p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('mpanel-'+id).classList.add('active');
}}
</script>
</body>
</html>"""
    return html


def inject_promo(html):
    """프로모 배너 CSS + HTML 강제 삽입"""
    # CSS 주입
    if "promo-banner" not in html:
        html = html.replace("</style>", PROMO_CSS + "\n</style>", 1)

    # HTML 주입 (3단계 폴백)
    if "<!-- PROMO_PLACEHOLDER -->" in html:
        html = html.replace("<!-- PROMO_PLACEHOLDER -->", PROMO_HTML, 1)
        print("  → 배너 삽입 (방법1)")
    elif "<!-- WEATHER -->" in html or "<!-- weather -->" in html:
        for marker in ["<!-- WEATHER -->", "<!-- weather -->"]:
            if marker in html:
                html = html.replace(marker, PROMO_HTML + "\n" + marker, 1)
                print("  → 배너 삽입 (방법2)")
                break
    elif '<div class="card">' in html:
        html = html.replace('<div class="card">', '<div class="card">\n' + PROMO_HTML, 1)
        print("  → 배너 삽입 (방법3)")
    else:
        print("  ⚠️ 배너 삽입 실패")
    return html


def push(html, date_str):
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True)
    subprocess.run(["git", "add", "index.html"], check=True)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        print("  → 변경없음, 스킵")
        return
    subprocess.run(["git", "commit", "-m", f"🦎 Daily briefing - {date_str}"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("  → git push 완료")


def main():
    kst  = datetime.timezone(datetime.timedelta(hours=9))
    now  = datetime.datetime.now(kst)
    days_ko = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
    days_en = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    months  = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]

    date_info = {
        "date_ko":  now.strftime("%Y년 %m월 %d일"),
        "date_en":  f"{months[now.month-1]} {now.year} · {days_en[now.weekday()]}",
        "day_num":  now.strftime("%d"),
        "day_ko":   days_ko[now.weekday()],
        "date_str": now.strftime("%Y-%m-%d"),
    }

    print(f"\n🦎 브리핑 생성 시작: {date_info['date_ko']} {date_info['day_ko']}")
    print("=" * 50)

    print("\n📺 [1/4] YouTube Shorts 검색 중...")
    youtube = get_youtube_shorts()
    print(f"  → {youtube['title'] if youtube else '없음'}")

    print("\n🤖 [2/4] Claude API HTML 생성 중...")

    # 1차: 데이터 수집
    data = collect_data(date_info)

    # Python으로 직접 HTML 조립 (API 호출 없음)
    html = build_html(data, youtube, date_info)
    print(f"  → HTML 생성 완료 ({len(html):,} bytes)")

    print("\n📤 [4/4] GitHub 푸시 중...")
    push(html, date_info["date_str"])

    print("\n" + "=" * 50)
    print(f"🎉 완료! https://크레노트.com?d={now.strftime('%Y%m%d')}")


if __name__ == "__main__":
    main()
