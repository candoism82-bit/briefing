#!/usr/bin/env python3
"""
🦎 Crested Gecko Community - Daily Briefing Auto-Generator
매일 아침 자동으로 브리핑 HTML을 생성해서 GitHub에 푸시합니다.
"""

import os
import subprocess
import datetime
from googleapiclient.discovery import build
import anthropic

# ═══════════════════════════════════════
# 환경변수에서 API 키 로드
# ═══════════════════════════════════════
YOUTUBE_API_KEY   = os.environ["YOUTUBE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# ═══════════════════════════════════════
# 고정 프로모 배너 CSS
# ═══════════════════════════════════════
PROMO_BANNER_CSS = """
/* ════════════════════════════
   LITTLE LIVES 홍보 배너
════════════════════════════ */
.promo-banner{background:linear-gradient(160deg,#0a1f08 0%,#1a3a15 50%,#0e2a0a 100%);padding:0;position:relative;overflow:hidden;border-bottom:3px solid #3d7a3a}
.promo-banner::before{content:'🌿🌿🌿🌿🌿🌿🌿🌿🌿🌿';position:absolute;top:-10px;left:0;right:0;font-size:40px;opacity:.05;letter-spacing:8px;line-height:1;pointer-events:none;white-space:nowrap;overflow:hidden}
.promo-inner{padding:22px 24px 20px;position:relative;z-index:1}
.promo-badge-row{display:flex;align-items:center;gap:8px;margin-bottom:14px}
.promo-badge{background:#3d7a3a;color:#c8f0a0;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.12em;text-transform:uppercase;padding:3px 10px;border-radius:20px;font-weight:500}
.promo-badge-line{flex:1;height:1px;background:rgba(255,255,255,.08)}
.promo-copy{text-align:center;margin-bottom:18px}
.promo-heart{font-size:28px;margin-bottom:8px;display:block;animation:heartbeat 1.8s ease infinite}
@keyframes heartbeat{0%,100%{transform:scale(1)}30%{transform:scale(1.18)}50%{transform:scale(1)}70%{transform:scale(1.1)}}
.promo-main-text{font-family:'Noto Serif KR',serif;font-size:18px;font-weight:900;color:#fff;line-height:1.55;margin-bottom:6px}
.promo-main-text em{color:#7ae050;font-style:normal}
.promo-sub-text{font-size:13px;color:rgba(255,255,255,.65);line-height:1.7;margin-top:4px}
.promo-sub-text strong{color:#a8e060;font-weight:700}
.promo-org-box{background:rgba(106,173,69,.12);border:1px solid rgba(106,173,69,.35);border-radius:8px;padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.promo-org-name{font-family:'Noto Serif KR',serif;font-size:16px;font-weight:900;color:#fff;display:flex;align-items:center;gap:6px;margin-bottom:4px}
.promo-org-name .bang{color:#7ae050;font-size:18px}
.promo-org-url{font-family:'DM Mono',monospace;font-size:11px;color:#6aad45;letter-spacing:.04em;text-decoration:none;border-bottom:1px solid rgba(106,173,69,.4);padding-bottom:1px}
.promo-qr-hint{text-align:center;flex-shrink:0}
.promo-qr-emoji{font-size:36px}
.promo-qr-label{font-family:'DM Mono',monospace;font-size:9px;color:rgba(255,255,255,.3);letter-spacing:.08em;margin-top:3px;display:block}
.promo-img-wrap{border-radius:8px;overflow:hidden;border:1px solid rgba(106,173,69,.25)}
.promo-img-wrap img{width:100%;display:block}
"""

# ═══════════════════════════════════════
# 고정 프로모 배너 HTML
# ═══════════════════════════════════════
PROMO_BANNER_HTML = """
<!-- ★ LITTLE LIVES 홍보 배너 -->
<div class="promo-banner">
  <div class="promo-inner">
    <div class="promo-badge-row">
      <span class="promo-badge">🌿 함께해요</span>
      <div class="promo-badge-line"></div>
      <span class="promo-badge">파충류 권익 보호</span>
    </div>
    <div class="promo-copy">
      <span class="promo-heart">♥️</span>
      <div class="promo-main-text">
        생명을 소중히 여기신다면<br>
        <em>함께해 주시고 힘을 실어주세요</em>
      </div>
      <div class="promo-sub-text">
        <strong>집사님들이 관심을 가져주셔야!</strong><br>
        더 좋은 환경에서 키우실 수 있습니다! 🦎
      </div>
    </div>
    <div class="promo-org-box">
      <div class="promo-org-left">
        <div class="promo-org-name">
          사단법인 작은생명공존연합
          <span class="bang">‼️</span>
        </div>
        <a class="promo-org-url" href="https://www.littlelives.or.kr/" target="_blank">
          🔗 www.littlelives.or.kr
        </a>
      </div>
      <div class="promo-qr-hint">
        <div class="promo-qr-emoji">🐊</div>
        <span class="promo-qr-label">Little Lives</span>
      </div>
    </div>
    <div class="promo-img-wrap">
      <img src="images/littlelives.png" alt="작은생명공존연합 야생생물법 변경안 안내">
    </div>
  </div>
</div>
"""


# ═══════════════════════════════════════
# 1. YouTube Shorts 검색
# ═══════════════════════════════════════
def get_youtube_shorts():
    """크레스티드 게코 관련 인기 Shorts 1개 가져오기"""
    try:
        youtube  = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        today    = datetime.datetime.utcnow()
        week_ago = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

        response = youtube.search().list(
            q="crested gecko",
            part="snippet",
            type="video",
            videoDuration="short",
            order="viewCount",
            publishedAfter=week_ago,
            maxResults=5,
        ).execute()

        # 최근 1주 결과 없으면 기간 확장
        if not response.get("items"):
            response = youtube.search().list(
                q="crested gecko cute",
                part="snippet",
                type="video",
                videoDuration="short",
                order="viewCount",
                maxResults=5,
            ).execute()

        items = response.get("items", [])
        if not items:
            return None

        item     = items[0]
        video_id = item["id"]["videoId"]
        return {
            "video_id":  video_id,
            "title":     item["snippet"]["title"],
            "channel":   item["snippet"]["channelTitle"],
            "embed_url": f"https://www.youtube.com/embed/{video_id}?autoplay=0",
            "watch_url": f"https://www.youtube.com/shorts/{video_id}",
        }
    except Exception as e:
        print(f"⚠️ YouTube API 오류: {e}")
        return None


# ═══════════════════════════════════════
# 2-A. 웹 검색으로 오늘 데이터 수집 (1차 호출)
# ═══════════════════════════════════════
def collect_daily_data(date_info):
    """웹 검색으로 날씨·뉴스·운세를 JSON 텍스트로 수집"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""
오늘은 {date_info['date_ko']} ({date_info['day_ko']})입니다.
웹 검색을 사용해 아래 데이터를 수집하고 JSON 형식으로만 반환하세요.
설명·마크다운 없이 JSON만 출력하세요.

{{
  "weather": {{
    "overview": "날씨 한줄 요약",
    "detail": "아침 최저/최고 기온, 특보 등 상세",
    "cities": [
      {{"name":"SEOUL","high":"?°","low":"?°","icon":"🌥"}},
      {{"name":"BUSAN","high":"?°","low":"?°","icon":"🌤"}},
      {{"name":"DAEGU","high":"?°","low":"?°","icon":"⛅"}},
      {{"name":"DAEJEON","high":"?°","low":"?°","icon":"🌥"}},
      {{"name":"GWANGJU","high":"?°","low":"?°","icon":"⛅"}},
      {{"name":"JEJU","high":"?°","low":"?°","icon":"🌦"}}
    ],
    "weekly": [
      {{"day":"오늘","icon":"🌥","high":"?°","low":"?°"}},
      {{"day":"화","icon":"☀","high":"?°","low":"?°"}},
      {{"day":"수","icon":"⛅","high":"?°","low":"?°"}},
      {{"day":"목","icon":"🌤","high":"?°","low":"?°"}},
      {{"day":"금","icon":"🌥","high":"?°","low":"?°"}},
      {{"day":"토","icon":"⛅","high":"?°","low":"?°"}},
      {{"day":"일","icon":"⛅","high":"?°","low":"?°"}}
    ]
  }},
  "economy_news": [
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}}
  ],
  "politics_news": [
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}},
    {{"title":"제목","summary":"한줄요약","url":"https://...","source":"출처명"}}
  ],
  "zodiac": [
    {{"sign":"쥐","emoji":"🐭","summary":"한줄요약",
      "years":[
        {{"year":"60년생","text":"운세 내용"}},
        {{"year":"72년생","text":"운세 내용"}},
        {{"year":"84년생","text":"운세 내용"}},
        {{"year":"96년생","text":"운세 내용"}},
        {{"year":"08년생","text":"운세 내용"}}
      ]}},
    {{"sign":"소","emoji":"🐮","summary":"한줄요약",
      "years":[
        {{"year":"61년생","text":"운세 내용"}},
        {{"year":"73년생","text":"운세 내용"}},
        {{"year":"85년생","text":"운세 내용"}},
        {{"year":"97년생","text":"운세 내용"}},
        {{"year":"09년생","text":"운세 내용"}}
      ]}},
    {{"sign":"호랑이","emoji":"🐯","summary":"한줄요약",
      "years":[
        {{"year":"62년생","text":"운세 내용"}},
        {{"year":"74년생","text":"운세 내용"}},
        {{"year":"86년생","text":"운세 내용"}},
        {{"year":"98년생","text":"운세 내용"}},
        {{"year":"10년생","text":"운세 내용"}}
      ]}},
    {{"sign":"토끼","emoji":"🐰","summary":"한줄요약",
      "years":[
        {{"year":"63년생","text":"운세 내용"}},
        {{"year":"75년생","text":"운세 내용"}},
        {{"year":"87년생","text":"운세 내용"}},
        {{"year":"99년생","text":"운세 내용"}},
        {{"year":"11년생","text":"운세 내용"}}
      ]}},
    {{"sign":"용","emoji":"🐲","summary":"한줄요약",
      "years":[
        {{"year":"64년생","text":"운세 내용"}},
        {{"year":"76년생","text":"운세 내용"}},
        {{"year":"88년생","text":"운세 내용"}},
        {{"year":"00년생","text":"운세 내용"}},
        {{"year":"12년생","text":"운세 내용"}}
      ]}},
    {{"sign":"뱀","emoji":"🐍","summary":"한줄요약",
      "years":[
        {{"year":"65년생","text":"운세 내용"}},
        {{"year":"77년생","text":"운세 내용"}},
        {{"year":"89년생","text":"운세 내용"}},
        {{"year":"01년생","text":"운세 내용"}},
        {{"year":"13년생","text":"운세 내용"}}
      ]}},
    {{"sign":"말","emoji":"🐴","summary":"한줄요약",
      "years":[
        {{"year":"66년생","text":"운세 내용"}},
        {{"year":"78년생","text":"운세 내용"}},
        {{"year":"90년생","text":"운세 내용"}},
        {{"year":"02년생","text":"운세 내용"}},
        {{"year":"14년생","text":"운세 내용"}}
      ]}},
    {{"sign":"양","emoji":"🐑","summary":"한줄요약",
      "years":[
        {{"year":"67년생","text":"운세 내용"}},
        {{"year":"79년생","text":"운세 내용"}},
        {{"year":"91년생","text":"운세 내용"}},
        {{"year":"03년생","text":"운세 내용"}},
        {{"year":"15년생","text":"운세 내용"}}
      ]}},
    {{"sign":"원숭이","emoji":"🐵","summary":"한줄요약",
      "years":[
        {{"year":"68년생","text":"운세 내용"}},
        {{"year":"80년생","text":"운세 내용"}},
        {{"year":"92년생","text":"운세 내용"}},
        {{"year":"04년생","text":"운세 내용"}},
        {{"year":"16년생","text":"운세 내용"}}
      ]}},
    {{"sign":"닭","emoji":"🐔","summary":"한줄요약",
      "years":[
        {{"year":"69년생","text":"운세 내용"}},
        {{"year":"81년생","text":"운세 내용"}},
        {{"year":"93년생","text":"운세 내용"}},
        {{"year":"05년생","text":"운세 내용"}},
        {{"year":"17년생","text":"운세 내용"}}
      ]}},
    {{"sign":"개","emoji":"🐶","summary":"한줄요약",
      "years":[
        {{"year":"70년생","text":"운세 내용"}},
        {{"year":"82년생","text":"운세 내용"}},
        {{"year":"94년생","text":"운세 내용"}},
        {{"year":"06년생","text":"운세 내용"}},
        {{"year":"18년생","text":"운세 내용"}}
      ]}},
    {{"sign":"돼지","emoji":"🐷","summary":"한줄요약",
      "years":[
        {{"year":"71년생","text":"운세 내용"}},
        {{"year":"83년생","text":"운세 내용"}},
        {{"year":"95년생","text":"운세 내용"}},
        {{"year":"07년생","text":"운세 내용"}},
        {{"year":"19년생","text":"운세 내용"}}
      ]}}
  ],
  "horoscope": [
    {{"sign":"양자리","emoji":"♈","date":"3.21~4.19","text":"운세"}},
    {{"sign":"황소자리","emoji":"♉","date":"4.20~5.20","text":"운세"}},
    {{"sign":"쌍둥이자리","emoji":"♊","date":"5.21~6.21","text":"운세"}},
    {{"sign":"게자리","emoji":"♋","date":"6.22~7.22","text":"운세"}},
    {{"sign":"사자자리","emoji":"♌","date":"7.23~8.22","text":"운세"}},
    {{"sign":"처녀자리","emoji":"♍","date":"8.23~9.22","text":"운세"}},
    {{"sign":"천칭자리","emoji":"♎","date":"9.23~10.23","text":"운세"}},
    {{"sign":"전갈자리","emoji":"♏","date":"10.24~11.21","text":"운세"}},
    {{"sign":"사수자리","emoji":"♐","date":"11.22~12.21","text":"운세"}},
    {{"sign":"염소자리","emoji":"♑","date":"12.22~1.19","text":"운세"}},
    {{"sign":"물병자리","emoji":"♒","date":"1.20~2.18","text":"운세"}},
    {{"sign":"물고기자리","emoji":"♓","date":"2.19~3.20","text":"운세"}}
  ],
  "meme_drips": ["뉴스 기반 드립1", "뉴스 기반 드립2", "뉴스 기반 드립3"]
}}
"""

    print("  [1차] 웹 검색으로 데이터 수집 중...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )

    # 응답에서 JSON 텍스트 추출
    raw = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw += block.text

    # JSON 파싱
    import json, re
    # 마크다운 코드블록 제거
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()

    # JSON 범위 추출
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("데이터 수집 실패 — JSON 없음")

    data = json.loads(raw[start:end])
    print(f"  [1차] 수집 완료 — 뉴스 {len(data.get('economy_news',[]))+len(data.get('politics_news',[]))}건, 운세 {len(data.get('zodiac',[]))}띠")
    return data


# ═══════════════════════════════════════
# 2-B. 수집한 데이터로 HTML 생성 (2차 호출, 웹 검색 없음)
# ═══════════════════════════════════════
def generate_html(youtube_data, date_info):
    """2단계: 데이터 수집 → HTML 생성 (토큰 분리로 잘림 방지)"""
    import json

    # 1차: 데이터 수집
    daily_data = collect_daily_data(date_info)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 유튜브 섹션 지시
    if youtube_data:
        youtube_instruction = f"""밈 존에 "📺 Shorts" 탭 추가 (맨 앞):
- 제목: {youtube_data['title']}
- 채널: {youtube_data['channel']}
- iframe src: {youtube_data['embed_url']}
- 바로가기: {youtube_data['watch_url']}
탭 순서: 📺 Shorts → 📹 GIF → 💬 드립 → 🖼 짤"""
    else:
        youtube_instruction = "유튜브 영상 없음 — 기존 GIF/드립/짤 탭 유지"

    # 템플릿 CSS 로드
    template_css = ""
    if os.path.exists("template.html"):
        with open("template.html", "r", encoding="utf-8") as f:
            content = f.read()
            # <style> 태그 안의 CSS만 추출
            import re
            m = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
            if m:
                template_css = m.group(1)[:6000]

    prompt = f"""
아래 데이터로 크레스티드 게코 커뮤니티 아침 브리핑 HTML을 생성하세요.
웹 검색 없이 제공된 데이터만 사용하세요.

=== 날짜 ===
날짜 숫자: {date_info['day_num']}
날짜 텍스트: {date_info['date_en']}
날짜 한국어: {date_info['date_ko']} ({date_info['day_ko']})

=== 오늘 데이터 ===
{json.dumps(daily_data, ensure_ascii=False, indent=2)}

=== 유튜브 ===
{youtube_instruction}

=== HTML 생성 규칙 ===
1. 캐시 방지 meta 태그 포함 (Cache-Control: no-cache, Pragma: no-cache, Expires: 0)
2. 헤더 블록 바로 다음 줄: <!-- PROMO_BANNER_PLACEHOLDER -->
3. 섹션 순서: 헤더 → 프로모배너placeholder → 날씨 → 경제뉴스 → 정치뉴스 → 띠별운세 → 별자리운세 → 밈존 → 푸터
4. 띠별 운세: 12띠 탭 전환형, 각 띠 클릭 시 생년별 5개 운세 표시
5. 별자리 운세: 12개 그리드
6. 밈 드립은 데이터의 meme_drips 사용
7. 아래 CSS 스타일 유지

=== CSS (유지할 것) ===
<style>
{template_css}
</style>

완전한 HTML 파일만 출력. <!DOCTYPE html>부터 </html>까지. 마크다운 없이.
"""

    print("  [2차] HTML 생성 중 (웹 검색 없음, 스트리밍)...")
    html_content = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            html_content += text

    # HTML 범위 추출
    if "<!DOCTYPE html>" in html_content:
        start = html_content.index("<!DOCTYPE html>")
        if "</html>" in html_content:
            end          = html_content.rindex("</html>") + 7
            html_content = html_content[start:end]
        else:
            html_content = html_content[start:]
            if "</body>" not in html_content:
                html_content += "\n</body>\n</html>"
            else:
                html_content += "\n</html>"
    else:
        print("  ⚠️ HTML 없음:")
        print(html_content[:500])
        raise ValueError("Claude API 응답에 HTML이 없습니다.")

    return html_content


# ═══════════════════════════════════════
# 3. 프로모 배너 강제 삽입 (3단계 폴백)
# ═══════════════════════════════════════
def inject_promo_banner(html_content):
    """
    작은생명공존연합 배너를 100% 확실하게 삽입.
    방법 1: placeholder 치환
    방법 2: 헤더 블록 끝 뒤 삽입
    방법 3: .card div 상단에 삽입 (최후 수단)
    """
    # CSS가 없으면 </style> 앞에 주입
    if "promo-banner" not in html_content and "</style>" in html_content:
        html_content = html_content.replace(
            "</style>",
            PROMO_BANNER_CSS + "\n</style>",
            1
        )
        print("  → 프로모 CSS 주입 완료")

    # 방법 1: placeholder 치환
    if "<!-- PROMO_BANNER_PLACEHOLDER -->" in html_content:
        html_content = html_content.replace(
            "<!-- PROMO_BANNER_PLACEHOLDER -->",
            PROMO_BANNER_HTML,
            1
        )
        print("  → 배너 삽입 완료 (방법1: placeholder)")
        return html_content

    # 방법 2: 헤더 끝 주석 뒤 삽입
    for marker in [
        "\n\n<!-- WEATHER -->",
        "\n<!-- WEATHER -->",
        "\n\n<!-- weather -->",
        "\n<!-- weather -->",
    ]:
        if marker in html_content:
            html_content = html_content.replace(
                marker,
                f"\n\n{PROMO_BANNER_HTML}{marker}",
                1
            )
            print("  → 배너 삽입 완료 (방법2: 헤더 뒤)")
            return html_content

    # 방법 3: card div 상단
    if '<div class="card">' in html_content:
        html_content = html_content.replace(
            '<div class="card">',
            f'<div class="card">\n{PROMO_BANNER_HTML}',
            1
        )
        print("  → 배너 삽입 완료 (방법3: card 상단)")
        return html_content

    print("  ⚠️ 배너 삽입 실패 — 수동 확인 필요")
    return html_content


# ═══════════════════════════════════════
# 4. GitHub에 index.html 푸시
# ═══════════════════════════════════════
def push_to_github(html_content, date_str):
    """index.html 파일에 쓰고 git으로 커밋·푸시"""
    # index.html 파일에 직접 쓰기 (GitHub Actions에서 레포가 이미 체크아웃됨)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("  → index.html 파일 저장 완료")

    # git 설정
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "config", "user.name",  "GitHub Actions"],      check=True)

    # 변경사항 커밋 & 푸시
    subprocess.run(["git", "add", "index.html"], check=True)

    # 변경사항이 없으면 커밋 스킵
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("  → 변경사항 없음, 커밋 스킵")
        return

    subprocess.run(["git", "commit", "-m", f"🦎 Daily briefing - {date_str}"], check=True)
    subprocess.run(["git", "push"],                                              check=True)
    print("  → git push 완료")


# ═══════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════
def main():
    kst     = datetime.timezone(datetime.timedelta(hours=9))
    now     = datetime.datetime.now(kst)
    days_ko = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
    days_en = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
    months  = ["JAN","FEB","MAR","APR","MAY","JUN",
               "JUL","AUG","SEP","OCT","NOV","DEC"]

    date_info = {
        "date_ko":  now.strftime("%Y년 %m월 %d일"),
        "date_en":  f"{months[now.month-1]} {now.year} · {days_en[now.weekday()]}",
        "day_num":  now.strftime("%d"),
        "day_ko":   days_ko[now.weekday()],
        "date_str": now.strftime("%Y-%m-%d"),
    }

    print(f"\n🦎 브리핑 생성 시작: {date_info['date_ko']} {date_info['day_ko']}")
    print("=" * 50)

    # 1. YouTube Shorts
    print("\n📺 [1/4] YouTube Shorts 검색 중...")
    youtube_data = get_youtube_shorts()
    print(f"  → {'선택: ' + youtube_data['title'] if youtube_data else '영상 없음, 스킵'}")

    # 2. HTML 생성
    print("\n🤖 [2/4] Claude API HTML 생성 중...")
    html_content = generate_html(youtube_data, date_info)
    print(f"  → 생성 완료 ({len(html_content):,} bytes)")

    # 3. 프로모 배너 강제 삽입
    print("\n💚 [3/4] 작은생명공존연합 배너 삽입 중...")
    html_content = inject_promo_banner(html_content)

    # 4. GitHub 푸시
    print("\n📤 [4/4] GitHub 푸시 중...")
    push_to_github(html_content, date_info["date_str"])

    print("\n" + "=" * 50)
    print(f"🎉 완료! URL: https://크레노트.com?d={now.strftime('%Y%m%d')}")


if __name__ == "__main__":
    main()
