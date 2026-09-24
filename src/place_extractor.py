#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Place Extractor Module.
Extracts places from YouTube or Blog links, categorizes them,
and saves them to the Google Maps master storage.
"""

import re
import json
import html
import urllib.request
import urllib.parse
from pathlib import Path
from .storage import add_place, CATEGORIES

# Category keyword dictionary for robust heuristic classification
CATEGORY_RULES = {
    "식당 및 카페": [
        "식당", "맛집", "카페", "cafe", "coffee", "디저트", "베이커리", "빵집", "바", "bar",
        "타파스", "tapas", "레스토랑", "restaurant", "음식점", "브런치", "라멘", "스시",
        "이자카야", "피자", "파스타", "와인", "맥주", "펍", "pub", "bistro", "비스트로",
        "bbq", "고기", "국수", "디저트카페", "베이크", "브루어리", "brewery", "라운지", "lounge"
    ],
    "숙박": [
        "호텔", "hotel", "호스텔", "hostel", "리조트", "resort", "숙소", "에어비앤비", "airbnb",
        "료칸", "게스트하우스", "guesthouse", "펜션", "비앤비", "b&b", "민박", "posada"
    ],
    "유적지 및 관광지": [
        "성당", "catedral", "cathedral", "성", "castle", "박물관", "museum", "미술관",
        "gallery", "사원", "신사", "temple", "shrine", "전망대", "observatory", "tower", "타워",
        "광장", "plaza", "palace", "궁전", "궁", "유적", "스튜디오", "테마파크", "기념관", "투어",
        "뮤지엄", "art center", "포럼", "forum", "시티뷰", "city view", "전망"
    ],
    "자연 및 공원": [
        "공원", "park", "해변", "beach", "playa", "cala", "바다", "산", "mountain", "계곡",
        "폭포", "waterfall", "정원", "garden", "호수", "lake", "곶", "cape", "숲", "forest"
    ],
    "쇼핑 및 시장": [
        "시장", "market", "mercado", "야시장", "백화점", "아울렛", "outlet", "쇼핑몰",
        "mall", "소품샵", "기념품", "souvenir", "마트", "슈퍼마켓", "store"
    ]
}


def classify_category(name, text_context=""):
    """Classify place into one of the 6 canonical categories."""
    haystack = f"{name} {text_context}".lower()
    
    # Hotel dining/cafe special handling: "호텔 카페", "호텔 라운지", "lounge" should be dining/cafe, not lodging
    if any(k in haystack for k in ["호텔 카페", "호텔 라운지", "호텔 레스토랑", "호텔 바", "hotel cafe", "hotel lounge", "라운지 카페", "라운지", "lounge"]):
        return "식당 및 카페"

    # Priority order for classification
    for cat in ["숙박", "식당 및 카페", "쇼핑 및 시장", "유적지 및 관광지", "자연 및 공원"]:
        keywords = CATEGORY_RULES[cat]
        for kw in keywords:
            if kw.lower() in haystack:
                return cat
                
    return "기타"


def normalize_region_hint(region, text_context=""):
    """Normalize or infer standardized region name (e.g. 일본 도쿄, 일본 후쿠오카)."""
    r = (region or "").strip()
    c = f"{r} {text_context}".lower()

    if any(k in c for k in ["도쿄", "tokyo", "東京"]):
        return "일본 도쿄"
    if any(k in c for k in ["후쿠오카", "fukuoka"]):
        return "일본 후쿠오카"
    if any(k in c for k in ["오사카", "osaka"]):
        return "일본 오사카"
    if any(k in c for k in ["삿포로", "sapporo"]):
        return "일본 삿포로"
    if any(k in c for k in ["스페인", "바르셀로나", "마드리드", "포르투갈"]):
        return "스페인_포르투갈"
    if any(k in c for k in ["대만", "타이베이", "가오슝"]):
        return "대만"
    if any(k in c for k in ["마카오"]):
        return "마카오"
    if any(k in c for k in ["하노이", "베트남", "다낭"]):
        return "베트남 하노이"
        
    return r or "기타"


import ssl

def fetch_url_content(url):
    """Fetch raw HTML / text content with custom User-Agent."""
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as response:
            content = response.read().decode("utf-8", errors="ignore")
            return content
    except Exception as e:
        print(f"[Warning] Failed to fetch URL directly: {e}")
        return ""


def extract_from_youtube(url, html_content=""):
    """Extract metadata and place mentions from YouTube video."""
    video_info = {"title": "", "description": "", "places": []}
    ctx = ssl._create_unverified_context()
    
    # Try oEmbed API for video title
    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            video_info["title"] = data.get("title", "")
    except Exception:
        pass

    if not html_content:
        html_content = fetch_url_content(url)

    # Parse title & description from HTML if missing
    if not video_info["title"]:
        title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
        if title_match:
            video_info["title"] = html.unescape(title_match.group(1)).replace(" - YouTube", "").strip()

    desc_match = re.search(r'"shortDescription":"(.*?)"(?:,"isCrawlable"|,"thumbnail")', html_content)
    if desc_match:
        try:
            raw_desc = desc_match.group(1)
            video_info["description"] = json.loads('"' + raw_desc.replace('"', '\\"') + '"')
        except Exception:
            video_info["description"] = bytes(desc_match.group(1), "utf-8").decode("unicode_escape", errors="ignore")

    # Combine text for place search
    full_text = f"{video_info['title']}\n{video_info['description']}"
    
    # Heuristic place extraction from description timestamps, bullet lines, and map links
    extracted_candidates = []
    lines = full_text.splitlines()
    for i, line in enumerate(lines):
        line_clean = line.strip()
        # Look for patterns like: 02:45 스시사카바 or 📍 츄레리아 or 1. 야키니쿠 규센닌 : https://maps.app.goo.gl/...
        map_url = ""
        # Check next 3 lines for a google maps link
        for next_line in lines[i:min(i+4, len(lines))]:
            map_match = re.search(r"(https://(?:maps\.app\.goo\.gl|goo\.gl/maps|www\.google\.com/maps)[^\s]+)", next_line)
            if map_match:
                map_url = map_match.group(1)
                break

        time_match = re.search(r"(?:\d{1,2}:\d{2})\s*(?:-\s*)?([A-Za-z0-9가-힣\s\'-]{2,30})", line_clean)
        if time_match:
            cand = time_match.group(1).strip()
            if cand and len(cand) > 1 and cand not in ["인트로", "잡설", "일정짜기", "가볼 만한 곳", "후쿠오카 감잡기"]:
                extracted_candidates.append({
                    "name": cand,
                    "context": line_clean,
                    "google_maps_url": map_url
                })
                continue
                
        pin_match = re.search(r"[📍📌🚩]\s*([A-Za-z0-9가-힣\s\'-]{2,30})", line_clean)
        if pin_match:
            cand = pin_match.group(1).strip()
            if cand and len(cand) > 1:
                extracted_candidates.append({
                    "name": cand,
                    "context": line_clean,
                    "google_maps_url": map_url
                })
                continue

        num_match = re.search(r"^\d+\.\s*([A-Za-z0-9가-힣\s\'-]{2,30})", line_clean)
        if num_match:
            cand = num_match.group(1).split(":")[0].strip()
            if cand and len(cand) > 1:
                extracted_candidates.append({
                    "name": cand,
                    "context": line_clean,
                    "google_maps_url": map_url
                })
                continue

    return video_info, extracted_candidates


def extract_from_naver_blog(url, html_content=""):
    """Extract places from Naver Blog (including Naver Map smartplace tags)."""
    # Convert desktop naver blog url to mobile url for cleaner parsing
    if "blog.naver.com" in url and "m.blog.naver.com" not in url:
        url = url.replace("blog.naver.com", "m.blog.naver.com")
        
    if not html_content:
        html_content = fetch_url_content(url)

    title = ""
    title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
    if title_match:
        title = html.unescape(title_match.group(1)).replace(" : 네이버 블로그", "").strip()

    extracted_candidates = []
    
    # Look for Naver SmartEditor Map widgets (se-map-info or place data)
    # e.g., data-place-name="...", "placeName":"..."
    place_names = set()
    for match in re.finditer(r'(?:data-place-name|data-name|placeName|title)=["\']([^"\']{2,40})["\']', html_content):
        name = html.unescape(match.group(1)).strip()
        if name and not any(k in name.lower() for k in ["naver", "blog", "네이버", "이미지", "profile", "post"]):
            place_names.add(name)

    # Search for bold headings, bullet lists, or pin emojis
    for match in re.finditer(r'[📍📌]\s*([가-힣A-Za-z0-9\s]{2,25})', html_content):
        cand = html.unescape(match.group(1)).strip()
        if cand:
            place_names.add(cand)

    for name in place_names:
        extracted_candidates.append((name, f"네이버 블로그 본문 언급: {title}"))

    return {"title": title, "url": url}, extracted_candidates


def extract_from_instagram(url, html_content=""):
    """
    Extract place mentions, metadata, and carousel slides from Instagram post or reel.
    Supports /p/, /reel/, /reels/ formats.
    Fetches embed (/embed/captioned/) and/or OpenGraph fallback with crawler User-Agent.
    """
    shortcode_match = re.search(r'instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)', url)
    shortcode = shortcode_match.group(1) if shortcode_match else ""

    info = {
        "title": "",
        "caption": "",
        "author": "",
        "slides": [],
        "places": []
    }

    ctx = ssl._create_unverified_context()
    
    # 1. Try captioned embed first (gives full caption + carousel slides in JSON)
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/" if shortcode else url
    embed_html = ""
    try:
        req = urllib.request.Request(
            embed_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            embed_html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        pass

    if embed_html:
        caption_match = re.search(r'<div class="Caption"[^>]*>(.*?)</div>', embed_html, re.DOTALL)
        if caption_match:
            c_text = html.unescape(caption_match.group(1))
            c_text = re.sub(r'<br\s*/?>', '\n', c_text)
            c_text = re.sub(r'<[^>]+>', ' ', c_text)
            info["caption"] = c_text.strip()
            
        author_match = re.search(r'<a class="CaptionUsername"[^>]*>(.*?)</a>', embed_html)
        if author_match:
            info["author"] = html.unescape(author_match.group(1)).strip()

        # Extract carousel slides if available
        parts = embed_html.split('display_url\\":\\"https:')
        if len(parts) > 1:
            seen_slides = set()
            for p in parts[1:]:
                raw_u = 'https:' + p.split('\\"')[0]
                clean_u = raw_u.replace(r'\\\/', '/').replace(r'\/', '/').replace('\\\\u0026', '&').replace('\\u0026', '&')
                base_id = clean_u.split('?')[0].split('/')[-1]
                if base_id not in seen_slides:
                    seen_slides.add(base_id)
                    info["slides"].append(clean_u)

    # 2. If caption is still empty or short, fetch original URL with crawler User-Agent
    if not info["caption"]:
        crawler_ua = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"
        try:
            req2 = urllib.request.Request(url, headers={"User-Agent": crawler_ua})
            with urllib.request.urlopen(req2, timeout=10, context=ctx) as resp2:
                crawler_html = resp2.read().decode("utf-8", errors="ignore")
                og_title = re.search(r'property="(?:og:title|twitter:title)" content="([^"]*)"', crawler_html)
                og_desc = re.search(r'property="(?:og:description|twitter:description|description)" content="([^"]*)"', crawler_html)
                t = html.unescape(og_title.group(1)) if og_title else ""
                d = html.unescape(og_desc.group(1)) if og_desc else ""
                info["caption"] = d or t
        except Exception:
            pass

    full_text = f"{info.get('author', '')}\n{info.get('caption', '')}"
    info["title"] = info["caption"].splitlines()[0][:60] if info["caption"] else "Instagram Post"

    # 3. Extract place candidates from caption text
    extracted_candidates = []
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    ignore_pin_words = ['영상 저장', '댓글', 'DM', '구글맵', '팔로우', '좋아요', '공유', '링크', '프로필', '클래스', '광고']

    current_cand = None
    for line in lines:
        # Check for pins / icons
        pin_match = re.search(r'^[📍📌🚩🏩🏛️☕🍽️]\s*(.+)', line)
        if pin_match:
            raw_name = pin_match.group(1).strip()
            if any(ign in raw_name for ign in ignore_pin_words):
                continue
            clean_name = re.sub(r'@[A-Za-z0-9_.]+', '', raw_name).strip()
            clean_name = re.sub(r'^\d+\.\s*', '', clean_name).strip()
            if len(clean_name) > 1:
                current_cand = {
                    "name": clean_name,
                    "context": line,
                    "details": [],
                    "google_maps_url": None
                }
                extracted_candidates.append(current_cand)
                continue

        # Numbered list pattern: 1. 명소이름 or [1] 명소이름
        num_match = re.search(r'^(?:[0-9]{1,2}\.|\([0-9]{1,2}\)|\[[0-9]{1,2}\])\s*([A-Za-z0-9가-힣\s\'-]{2,40})', line)
        if num_match:
            cand = num_match.group(1).split(":")[0].strip()
            cand_clean = re.sub(r'@[A-Za-z0-9_.]+', '', cand).strip()
            if len(cand_clean) > 1 and not any(ign in cand_clean for ign in ignore_pin_words):
                current_cand = {
                    "name": cand_clean,
                    "context": line,
                    "details": [],
                    "google_maps_url": None
                }
                extracted_candidates.append(current_cand)
                continue

        # If we have a current candidate, attach subsequent details like address or operating hours
        if current_cand:
            if line.startswith('•') or line.startswith('⏰') or 'Tokyo' in line or '일본' in line or '~' in line or 'Chome' in line or '〒' in line or 'City' in line or '구' in line or '로' in line:
                detail_clean = line.lstrip('•⏰ ').strip()
                if detail_clean:
                    current_cand["details"].append(detail_clean)

    for cand in extracted_candidates:
        if cand.get("details"):
            cand["context"] = f"{cand['context']} ({', '.join(cand['details'])})"

    return info, extracted_candidates


def process_url_and_save_places(url, manual_places=None, region_hint=""):
    """
    Main extraction function.
    Can accept manually confirmed places or extract automatically.
    Returns list of saved place records.
    """
    saved_results = []
    
    # If user/agent already parsed the places from LLM/content inspection
    if manual_places and isinstance(manual_places, list):
        for item in manual_places:
            name = item.get("name", "").strip()
            if not name:
                continue
            cat = item.get("category") or classify_category(name, item.get("notes", ""))
            tag = item.get("tag", "")
            raw_region = item.get("region") or region_hint
            region = normalize_region_hint(raw_region, f"{name} {tag} {item.get('notes', '')}")
            notes = item.get("notes", f"출처 링크: {url}")
            gmaps_url = item.get("google_maps_url")
            
            place, is_dup = add_place(
                name=name,
                category=cat,
                tag=tag,
                region=region,
                notes=notes,
                source_url=url,
                google_maps_url=gmaps_url,
                auto_push=False
            )
            saved_results.append({
                "place": place,
                "is_duplicate": is_dup,
                "action": "updated" if is_dup else "added"
            })
        if saved_results:
            try:
                from .git_sync import git_auto_push
                git_auto_push(f"feat(places): 수집 장소 {len(saved_results)}개 자동 동기화 ({url})")
            except Exception:
                pass
        return saved_results

    # Automated extraction
    content_title = ""
    if "youtube.com" in url or "youtu.be" in url:
        info, candidates = extract_from_youtube(url)
        content_title = info.get("title", "")
    elif "blog.naver.com" in url:
        info, candidates = extract_from_naver_blog(url)
        content_title = info.get("title", "")
    elif "instagram.com" in url:
        info, candidates = extract_from_instagram(url)
        content_title = info.get("title", "")
    else:
        # Generic website / Tistory
        html_content = fetch_url_content(url)
        title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE)
        content_title = html.unescape(title_match.group(1)).strip() if title_match else url
        candidates = []
        # Pattern search
        for match in re.finditer(r'[📍📌🚩]\s*([A-Za-z0-9가-힣\s\'-]{2,30})', html_content):
            candidates.append((match.group(1).strip(), "본문 발췌"))

    # Auto-infer & normalize region
    cand_text = " ".join(c.get("name", "") + " " + c.get("context", "") if isinstance(c, dict) else str(c) for c in candidates)
    region_hint = normalize_region_hint(region_hint, f"{url} {content_title} {cand_text}")

    # Save candidates
    for item in candidates:
        if isinstance(item, dict):
            name = item.get("name", "").strip()
            context = item.get("context", "")
            gmaps_url = item.get("google_maps_url")
            details = item.get("details", [])
        else:
            name, context = item
            gmaps_url = None
            details = []

        if not name:
            continue

        cat = classify_category(name, f"{content_title} {context}")
        
        detail_note = f" ({'; '.join(details)})" if details else ""
        item_region = normalize_region_hint(region_hint, f"{name} {context} {detail_note}")
        
        place, is_dup = add_place(
            name=name,
            category=cat,
            tag=context[:60],
            region=item_region,
            notes=f"수집 출처: {content_title} ({url}){detail_note}",
            source_url=url,
            google_maps_url=gmaps_url,
            auto_push=False
        )
        saved_results.append({
            "place": place,
            "is_duplicate": is_dup,
            "action": "updated" if is_dup else "added"
        })

    if saved_results:
        try:
            from .git_sync import git_auto_push
            title_summary = f" ({content_title[:25]})" if content_title else ""
            git_auto_push(f"feat(places): 수집 장소 {len(saved_results)}개 자동 동기화{title_summary}")
        except Exception:
            pass

    return saved_results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Extracting places from: {test_url}")
        res = process_url_and_save_places(test_url)
        print(f"Result: {json.dumps(res, ensure_ascii=False, indent=2)}")
    else:
        print("Usage: python3 place_extractor.py <URL>")
