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
# 2. Claude API로 HTML 생성
# ═══════════════════════════════════════
def generate_html(youtube_data, date_info):
    """Claude API로 오늘 브리핑 HTML 생성 (뉴스·운세·날씨 웹 검색 포함)"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 유튜브 섹션 지시
    if youtube_data:
        youtube_instruction = f"""
[유튜브 Shorts 정보]
- 제목: {youtube_data['title']}
- 채널: {youtube_data['channel']}
- embed URL: {youtube_data['embed_url']}
- 바로가기 URL: {youtube_data['watch_url']}
밈 존에 "📺 Shorts" 탭을 추가하고 위 영상을 iframe으로 임베드해주세요.
탭 순서: 📺 Shorts → 📹 GIF → 💬 드립 → 🖼 짤
"""
    else:
        youtube_instruction = "유튜브 영상 없음 — 밈 존은 GIF/드립/짤 탭만 유지"

    # 템플릿 로드
    template_html = ""
    if os.path.exists("template.html"):
        with open("template.html", "r", encoding="utf-8") as f:
            template_html = f.read()
            # CSS 앞부분만 전달 (토큰 절약)
            template_html = template_html[:8000]

    prompt = f"""
오늘은 {date_info['date_ko']} ({date_info['day_ko']})입니다.

크레스티드 게코 커뮤니티 아침 브리핑 HTML을 생성해주세요.
웹 검색으로 아래 데이터를 직접 수집해서 채워주세요.

=== 수집할 데이터 (웹 검색 필수) ===
1. 오늘 전국 날씨 (서울/부산/대구/대전/광주/제주 최저·최고 기온, 날씨 개요, 서울 주간 예보)
2. 오늘 경제/주식 뉴스 4건 (제목 + 한줄요약 + 출처URL)
3. 오늘 정치/사회 뉴스 4건 (제목 + 한줄요약 + 출처URL)
4. 오늘 띠별 운세 12띠 전체 (각 띠별로 생년별 운세 5개씩, 예: 72년/84년/96년/08년/20년)
5. 오늘 별자리 운세 12개 전체

=== 유튜브 ===
{youtube_instruction}

=== HTML 생성 규칙 ===
- 날짜 숫자 헤더: {date_info['day_num']}
- 날짜 텍스트 헤더: {date_info['date_en']}
- 캐시 방지 meta 태그 반드시 포함 (Cache-Control: no-cache, Pragma: no-cache, Expires: 0)
- 헤더 블록(<!-- HEADER --> ~ </div>) 바로 다음 줄에 정확히 아래 텍스트 삽입:
  <!-- PROMO_BANNER_PLACEHOLDER -->
- 밈 드립 3개는 오늘 뉴스 키워드 기반으로 새로 작성
- 아래 템플릿의 CSS 및 구조 유지

=== CSS 템플릿 참고 ===
{template_html}

완전한 HTML 파일만 출력하세요. <!DOCTYPE html>부터 </html>까지만, 마크다운 없이.
"""

    print("  Claude API 호출 중 (웹 검색 포함)...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )

    # 응답에서 HTML 텍스트 추출
    html_content = ""
    for block in response.content:
        if hasattr(block, "text"):
            html_content += block.text

    # HTML 범위만 추출
    if "<!DOCTYPE html>" in html_content:
        start = html_content.index("<!DOCTYPE html>")
        # </html> 없을 경우 대비 (웹 검색 블록이 섞인 경우)
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
        # HTML이 전혀 없으면 재시도
        print("  ⚠️ HTML 없음 — 응답 내용 확인:")
        print(html_content[:500])
        raise ValueError("Claude API 응답에 HTML이 없습니다. 재시도 필요.")

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
