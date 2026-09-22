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
        "bbq", "고기", "국수", "디저트카페", "베이크", "브루어리", "brewery"
    ],
    "숙박": [
        "호텔", "hotel", "호스텔", "hostel", "리조트", "resort", "숙소", "에어비앤비", "airbnb",
        "료칸", "게스트하우스", "guesthouse", "펜션", "비앤비", "b&b", "민박", "posada"
    ],
    "유적지 및 관광지": [
        "성당", "catedral", "cathedral", "성", "castle", "박물관", "museum", "미술관",
        "gallery", "사원", "신사", "temple", "shrine", "전망대", "observatory", "tower", "타워",
        "광장", "plaza", "palace", "궁전", "궁", "유적", "스튜디오", "테마파크", "기념관", "투어"
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
    
    # Priority order for classification
    for cat in ["숙박", "식당 및 카페", "쇼핑 및 시장", "유적지 및 관광지", "자연 및 공원"]:
        keywords = CATEGORY_RULES[cat]
        for kw in keywords:
            if kw.lower() in haystack:
                return cat
                
    return "기타"


def fetch_url_content(url):
    """Fetch raw HTML / text content with custom User-Agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            content = response.read().decode("utf-8", errors="ignore")
            return content
    except Exception as e:
        print(f"[Warning] Failed to fetch URL directly: {e}")
        return ""


def extract_from_youtube(url, html_content=""):
    """Extract metadata and place mentions from YouTube video."""
    video_info = {"title": "", "description": "", "places": []}
    
    # Try oEmbed API for video title
    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
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

    desc_match = re.search(r'"shortDescription":"(.*?)"', html_content)
    if desc_match:
        video_info["description"] = bytes(desc_match.group(1), "utf-8").decode("unicode_escape", errors="ignore")

    # Combine text for place search
    full_text = f"{video_info['title']}\n{video_info['description']}"
    
    # Heuristic place extraction from description timestamps or bullet lines
    # e.g., 01:23 [식당이름] or 1. 장소이름 or 📍 장소이름
    extracted_candidates = []
    lines = full_text.splitlines()
    for line in lines:
        line_clean = line.strip()
        # Look for patterns like: 02:45 바르셀로나 사그라다 파밀리아 or 📍 츄레리아
        time_match = re.search(r"(?:\d{1,2}:\d{2})\s*(?:-\s*)?([A-Za-z0-9가-힣\s\'-]{2,30})", line_clean)
        if time_match:
            cand = time_match.group(1).strip()
            if cand and len(cand) > 1:
                extracted_candidates.append((cand, line_clean))
                continue
                
        pin_match = re.search(r"[📍📌🚩]\s*([A-Za-z0-9가-힣\s\'-]{2,30})", line_clean)
        if pin_match:
            cand = pin_match.group(1).strip()
            if cand and len(cand) > 1:
                extracted_candidates.append((cand, line_clean))
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
            region = item.get("region", region_hint)
            notes = item.get("notes", f"출처 링크: {url}")
            
            place, is_dup = add_place(
                name=name,
                category=cat,
                tag=tag,
                region=region,
                notes=notes,
                source_url=url
            )
            saved_results.append({
                "place": place,
                "is_duplicate": is_dup,
                "action": "updated" if is_dup else "added"
            })
        return saved_results

    # Automated extraction
    if "youtube.com" in url or "youtu.be" in url:
        info, candidates = extract_from_youtube(url)
        content_title = info.get("title", "")
    elif "blog.naver.com" in url:
        info, candidates = extract_from_naver_blog(url)
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

    # Save candidates
    for name, context in candidates:
        cat = classify_category(name, f"{content_title} {context}")
        place, is_dup = add_place(
            name=name,
            category=cat,
            tag=context[:50],
            region=region_hint,
            notes=f"수집 출처: {content_title} ({url})",
            source_url=url
        )
        saved_results.append({
            "place": place,
            "is_duplicate": is_dup,
            "action": "updated" if is_dup else "added"
        })

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
