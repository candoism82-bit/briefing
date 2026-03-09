#!/usr/bin/env python3
"""
🦎 Crested Gecko Community - Daily Briefing Auto-Generator
매일 아침 자동으로 브리핑 HTML을 생성해서 GitHub에 푸시합니다.
"""

import os
import json
import base64
import datetime
import requests
from googleapiclient.discovery import build
import anthropic
from github import Github

# ═══════════════════════════════════════
# 환경변수에서 API 키 로드
# ═══════════════════════════════════════
YOUTUBE_API_KEY   = os.environ["YOUTUBE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GITHUB_TOKEN      = os.environ["GITHUB_TOKEN"]  # GitHub Actions에서 자동 제공
GITHUB_REPO       = "candoisr/briefing"          # 본인 레포로 변경

# ═══════════════════════════════════════
# 1. YouTube Shorts 검색
# ═══════════════════════════════════════
def get_youtube_shorts():
    """크레스티드 게코 관련 인기 Shorts 1개 가져오기"""
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        
        today = datetime.datetime.utcnow()
        week_ago = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        response = youtube.search().list(
            q="crested gecko",
            part="snippet",
            type="video",
            videoDuration="short",       # Shorts 필터
            order="viewCount",
            publishedAfter=week_ago,
            maxResults=5,
            relevanceLanguage="ko",
        ).execute()
        
        # 결과가 없으면 기간 확장
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
        
        # 첫 번째 영상 선택
        item = items[0]
        video_id    = item["id"]["videoId"]
        title       = item["snippet"]["title"]
        channel     = item["snippet"]["channelTitle"]
        description = item["snippet"]["description"][:100]
        
        return {
            "video_id":    video_id,
            "title":       title,
            "channel":     channel,
            "description": description,
            "embed_url":   f"https://www.youtube.com/embed/{video_id}",
            "watch_url":   f"https://www.youtube.com/shorts/{video_id}",
        }
    except Exception as e:
        print(f"YouTube API 오류: {e}")
        return None


# ═══════════════════════════════════════
# 2. 오늘의 뉴스 검색 (웹 검색)
# ═══════════════════════════════════════
def get_news_data(date_str):
    """Claude API의 web_search 툴로 뉴스 수집"""
    # Claude API 호출 시 web_search 툴 사용 (아래 generate_html에서 통합 처리)
    return date_str


# ═══════════════════════════════════════
# 3. Claude API로 HTML 생성
# ═══════════════════════════════════════
def generate_html(youtube_data, date_info):
    """Claude API에 모든 데이터를 전달해서 완성된 HTML 생성"""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    youtube_section = ""
    if youtube_data:
        youtube_section = f"""
오늘의 추천 유튜브 Shorts:
- 제목: {youtube_data['title']}
- 채널: {youtube_data['channel']}
- 영상 ID: {youtube_data['video_id']}
- 임베드 URL: {youtube_data['embed_url']}
- 바로가기 URL: {youtube_data['watch_url']}
"""
    
    prompt = f"""
오늘은 {date_info['date_ko']}입니다.

아래 조건에 맞는 크레스티드 게코 커뮤니티 아침 브리핑 HTML을 생성해주세요.

=== 수집할 데이터 (웹 검색으로 직접 찾아주세요) ===

1. 오늘의 띠별 운세 (생년별로 각각 다른 운세, 쥐/소/호랑이/토끼/용/뱀/말/양/원숭이/닭/개/돼지띠)
2. 오늘의 별자리 운세 (양자리~물고기자리 12개)
3. 오늘의 경제/주식 뉴스 4건 (제목 + 한줄요약 + 출처URL)
4. 오늘의 정치/사회 뉴스 4건 (제목 + 한줄요약 + 출처URL)
5. 오늘의 날씨 (전국 주요 도시 기온 + 날씨 개요)

{youtube_section}

=== HTML 구조 ===

아래 CSS와 HTML 구조를 그대로 유지하면서 오늘 날짜의 실제 데이터로 채워주세요.

[중요 사항]
- 날짜: {date_info['date_ko']} ({date_info['day_ko']})
- 헤더의 날짜 숫자: {date_info['day_num']}
- 헤더의 날짜 텍스트: {date_info['date_en']}
- 캐시 방지 meta 태그 반드시 포함
- 유튜브 영상은 밈 존 탭에 "📺 Shorts" 탭으로 추가 (GIF/드립/짤 탭과 함께)
- 밈 드립은 오늘 뉴스 키워드 기반으로 새로 작성
- 작은생명공존연합 홍보 배너는 헤더 아래에 반드시 포함

=== 기존 HTML 템플릿 (CSS 및 구조 유지) ===

{open('/home/runner/work/briefing/briefing/template.html').read() if os.path.exists('/home/runner/work/briefing/briefing/template.html') else get_template()}

완전한 HTML 파일만 출력해주세요. 설명이나 마크다운 없이 <!DOCTYPE html>부터 </html>까지만요.
"""

    print("Claude API 호출 중...")
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    
    # 응답에서 HTML 추출
    html_content = ""
    for block in response.content:
        if block.type == "text":
            html_content += block.text
    
    # HTML만 추출 (혹시 앞뒤에 텍스트가 있을 경우)
    if "<!DOCTYPE html>" in html_content:
        start = html_content.index("<!DOCTYPE html>")
        end   = html_content.rindex("</html>") + 7
        html_content = html_content[start:end]
    
    return html_content


# ═══════════════════════════════════════
# 4. 템플릿 HTML 로드 (로컬 fallback)
# ═══════════════════════════════════════
def get_template():
    """템플릿 파일이 없을 경우 기본 구조 반환"""
    template_path = "template.html"
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<!-- 템플릿 없음 -->"


# ═══════════════════════════════════════
# 5. GitHub에 index.html 푸시
# ═══════════════════════════════════════
def push_to_github(html_content, date_str):
    """GitHub 레포에 index.html 업데이트"""
    try:
        g    = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # 현재 파일의 SHA 가져오기 (업데이트에 필요)
        try:
            current_file = repo.get_contents("index.html")
            sha = current_file.sha
            repo.update_file(
                path="index.html",
                message=f"🦎 Daily briefing update - {date_str}",
                content=html_content,
                sha=sha,
            )
            print(f"✅ index.html 업데이트 완료: {date_str}")
        except Exception:
            # 파일이 없으면 새로 생성
            repo.create_file(
                path="index.html",
                message=f"🦎 Daily briefing create - {date_str}",
                content=html_content,
            )
            print(f"✅ index.html 신규 생성 완료: {date_str}")
            
    except Exception as e:
        print(f"GitHub 푸시 오류: {e}")
        raise


# ═══════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════
def main():
    # 한국 시간 기준 날짜
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(kst)
    
    date_info = {
        "date_ko":  now.strftime("%Y년 %m월 %d일"),
        "date_en":  now.strftime("%b %Y · ") + ["MON","TUE","WED","THU","FRI","SAT","SUN"][now.weekday()],
        "day_num":  now.strftime("%d"),
        "day_ko":   ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"][now.weekday()],
        "date_str": now.strftime("%Y-%m-%d"),
    }
    
    print(f"🦎 브리핑 생성 시작: {date_info['date_ko']} {date_info['day_ko']}")
    
    # 1. YouTube Shorts 검색
    print("📺 YouTube Shorts 검색 중...")
    youtube_data = get_youtube_shorts()
    if youtube_data:
        print(f"  → 영상 선택: {youtube_data['title']}")
    else:
        print("  → YouTube 영상 없음, 스킵")
    
    # 2. Claude API로 HTML 생성 (뉴스/운세 검색 포함)
    print("🤖 Claude API로 HTML 생성 중...")
    html_content = generate_html(youtube_data, date_info)
    print(f"  → HTML 생성 완료 ({len(html_content):,} bytes)")
    
    # 3. GitHub 푸시
    print("📤 GitHub 푸시 중...")
    push_to_github(html_content, date_info["date_str"])
    
    print(f"\n🎉 완료! 브리핑 URL: https://크레노트.com?d={now.strftime('%Y%m%d')}")


if __name__ == "__main__":
    main()
