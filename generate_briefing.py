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


def collect_data(date_info):
    """1차: 웹 검색으로 데이터 수집 → JSON 반환"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = (
        f"오늘 {date_info['date_ko']} 한국 데이터를 웹 검색해서 아래 JSON 형식으로만 반환. 설명 없이 JSON만.\n"
        '{"weather":{"overview":"","detail":"","cities":[{"name":"SEOUL","high":"","low":"","icon":"🌥"},{"name":"BUSAN","high":"","low":"","icon":"🌤"},{"name":"DAEGU","high":"","low":"","icon":"⛅"},{"name":"DAEJEON","high":"","low":"","icon":"🌥"},{"name":"GWANGJU","high":"","low":"","icon":"⛅"},{"name":"JEJU","high":"","low":"","icon":"🌦"}],"weekly":[{"day":"오늘","icon":"","high":"","low":""},{"day":"화","icon":"","high":"","low":""},{"day":"수","icon":"","high":"","low":""},{"day":"목","icon":"","high":"","low":""},{"day":"금","icon":"","high":"","low":""},{"day":"토","icon":"","high":"","low":""},{"day":"일","icon":"","high":"","low":""}]},'
        '"economy_news":[{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""}],'
        '"politics_news":[{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""},{"title":"","summary":"","url":"","source":""}],'
        '"zodiac":[{"sign":"쥐","emoji":"🐭","summary":"","years":[{"year":"60년생","text":""},{"year":"72년생","text":""},{"year":"84년생","text":""},{"year":"96년생","text":""},{"year":"08년생","text":""}]},{"sign":"소","emoji":"🐮","summary":"","years":[{"year":"61년생","text":""},{"year":"73년생","text":""},{"year":"85년생","text":""},{"year":"97년생","text":""},{"year":"09년생","text":""}]},{"sign":"호랑이","emoji":"🐯","summary":"","years":[{"year":"62년생","text":""},{"year":"74년생","text":""},{"year":"86년생","text":""},{"year":"98년생","text":""},{"year":"10년생","text":""}]},{"sign":"토끼","emoji":"🐰","summary":"","years":[{"year":"63년생","text":""},{"year":"75년생","text":""},{"year":"87년생","text":""},{"year":"99년생","text":""},{"year":"11년생","text":""}]},{"sign":"용","emoji":"🐲","summary":"","years":[{"year":"64년생","text":""},{"year":"76년생","text":""},{"year":"88년생","text":""},{"year":"00년생","text":""},{"year":"12년생","text":""}]},{"sign":"뱀","emoji":"🐍","summary":"","years":[{"year":"65년생","text":""},{"year":"77년생","text":""},{"year":"89년생","text":""},{"year":"01년생","text":""},{"year":"13년생","text":""}]},{"sign":"말","emoji":"🐴","summary":"","years":[{"year":"66년생","text":""},{"year":"78년생","text":""},{"year":"90년생","text":""},{"year":"02년생","text":""},{"year":"14년생","text":""}]},{"sign":"양","emoji":"🐑","summary":"","years":[{"year":"67년생","text":""},{"year":"79년생","text":""},{"year":"91년생","text":""},{"year":"03년생","text":""},{"year":"15년생","text":""}]},{"sign":"원숭이","emoji":"🐵","summary":"","years":[{"year":"68년생","text":""},{"year":"80년생","text":""},{"year":"92년생","text":""},{"year":"04년생","text":""},{"year":"16년생","text":""}]},{"sign":"닭","emoji":"🐔","summary":"","years":[{"year":"69년생","text":""},{"year":"81년생","text":""},{"year":"93년생","text":""},{"year":"05년생","text":""},{"year":"17년생","text":""}]},{"sign":"개","emoji":"🐶","summary":"","years":[{"year":"70년생","text":""},{"year":"82년생","text":""},{"year":"94년생","text":""},{"year":"06년생","text":""},{"year":"18년생","text":""}]},{"sign":"돼지","emoji":"🐷","summary":"","years":[{"year":"71년생","text":""},{"year":"83년생","text":""},{"year":"95년생","text":""},{"year":"07년생","text":""},{"year":"19년생","text":""}]}],'
        '"horoscope":[{"sign":"양자리","emoji":"♈","date":"3.21~4.19","text":""},{"sign":"황소자리","emoji":"♉","date":"4.20~5.20","text":""},{"sign":"쌍둥이자리","emoji":"♊","date":"5.21~6.21","text":""},{"sign":"게자리","emoji":"♋","date":"6.22~7.22","text":""},{"sign":"사자자리","emoji":"♌","date":"7.23~8.22","text":""},{"sign":"처녀자리","emoji":"♍","date":"8.23~9.22","text":""},{"sign":"천칭자리","emoji":"♎","date":"9.23~10.23","text":""},{"sign":"전갈자리","emoji":"♏","date":"10.24~11.21","text":""},{"sign":"사수자리","emoji":"♐","date":"11.22~12.21","text":""},{"sign":"염소자리","emoji":"♑","date":"12.22~1.19","text":""},{"sign":"물병자리","emoji":"♒","date":"1.20~2.18","text":""},{"sign":"물고기자리","emoji":"♓","date":"2.19~3.20","text":""}],'
        '"meme_drips":["","",""]}'
    )
    print("  [1차] 웹 검색 데이터 수집 중...")
    res = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    raw = "".join(b.text for b in res.content if hasattr(b, "text"))
    raw = re.sub(r"```json\s*|```", "", raw).strip()
    s, e = raw.find("{"), raw.rfind("}") + 1
    if s == -1: raise ValueError("JSON 없음")
    raw_json = raw[s:e]

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as err:
        print(f"  ⚠️ JSON 오류({err}) — json_repair로 자동 수정 중...")
        from json_repair import repair_json
        data = json.loads(repair_json(raw_json))
        print("  → 수정 완료")

    print(f"  [1차] 완료 — 뉴스 {len(data.get('economy_news',[]))+len(data.get('politics_news',[]))}건, 운세 {len(data.get('zodiac',[]))}띠")
    return data


def build_html(data, youtube, date_info):
    """2차: 데이터 → HTML (웹 검색 없음, 65초 대기 후 호출)"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    yt_block = ""
    if youtube:
        yt_block = f'밈 존 맨 앞에 "📺 Shorts" 탭 추가: iframe src="{youtube["embed"]}" / 링크={youtube["url"]} / 제목={youtube["title"]}'

    prompt = f"""
아래 JSON 데이터로 크레스티드 게코 커뮤니티 아침 브리핑 HTML을 생성하세요.

날짜: {date_info['day_num']} / {date_info['date_en']} / {date_info['date_ko']}
유튜브: {yt_block or '없음'}

데이터:
{json.dumps(data, ensure_ascii=False)}

요구사항:
- <meta http-equiv="Cache-Control" content="no-cache"> 포함
- 헤더 바로 뒤 <!-- PROMO_PLACEHOLDER --> 삽입
- 섹션순서: 헤더→프로모→날씨→경제뉴스→정치뉴스→띠별운세(탭형)→별자리운세→밈존→푸터
- 다크 모바일 테마 (배경 #0d1117, 카드 #161b22)
- 띠별운세: 탭 클릭시 생년별 운세 5개 표시
- 완전한 HTML만 출력, <!DOCTYPE html>~</html>, 마크다운 없이
"""

    print("  [2차] HTML 생성 중 (스트리밍)...")
    html = ""
    with client.messages.stream(
        model="claude-sonnet-4-6", max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            html += text

    # HTML 범위 추출
    if "<!DOCTYPE html>" in html:
        html = html[html.index("<!DOCTYPE html>"):]
        if "</html>" in html:
            html = html[:html.rindex("</html>") + 7]
        elif "</body>" in html:
            html += "\n</html>"
        else:
            html += "\n</body></html>"
    else:
        raise ValueError("HTML 없음")
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

    # ★ 핵심: 65초 대기 (rate limit 초기화)
    print("  ⏳ rate limit 대기 중 (65초)...")
    time.sleep(65)

    # 2차: HTML 생성
    html = build_html(data, youtube, date_info)
    print(f"  → HTML 생성 완료 ({len(html):,} bytes)")

    print("\n💚 [3/4] 프로모 배너 삽입 중...")
    html = inject_promo(html)

    print("\n📤 [4/4] GitHub 푸시 중...")
    push(html, date_info["date_str"])

    print("\n" + "=" * 50)
    print(f"🎉 완료! https://크레노트.com?d={now.strftime('%Y%m%d')}")


if __name__ == "__main__":
    main()
