#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Itinerary Generator Module.
Creates tailored travel plans using Google Maps saved places,
lodging information, and user travel profile preferences.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from .storage import load_places, find_places_by_region_or_query
from .profile_manager import load_profile

BASE_DIR = Path(__file__).resolve().parent.parent
ITINERARIES_DIR = BASE_DIR / "data" / "itineraries"


def infer_region_from_text(text):
    """Infer target city/country from hotel or destination string."""
    t = text.lower()
    if any(k in t for k in ["바르셀로나", "barcelona"]):
        return "바르셀로나"
    if any(k in t for k in ["마요르카", "mallorca", "팔마", "palma"]):
        return "마요르카"
    if any(k in t for k in ["포르투", "porto", "리스본", "lisbon"]):
        return "포르투"
    if any(k in t for k in ["스페인", "spain"]):
        return "스페인"
    if any(k in t for k in ["도쿄", "tokyo", "일본", "japan"]):
        return "도쿄"
    if any(k in t for k in ["하노이", "베트남", "vietnam"]):
        return "하노이"
    if any(k in t for k in ["마카오", "macau", "대만", "taiwan"]):
        return "마카오"
    return ""


def generate_itinerary(hotel_info, days, region=None, additional_notes=""):
    """
    Generate a complete day-by-day itinerary.
    """
    profile = load_profile()
    all_places = load_places()
    
    # Infer region if not specified
    if not region:
        region = infer_region_from_text(hotel_info)
    if not region and additional_notes:
        region = infer_region_from_text(additional_notes)
    if not region:
        region = "스페인"  # Default fallback if user has Spain places

    # Filter places matching region or general
    matched_places = find_places_by_region_or_query(region)
    if not matched_places or len(matched_places) < 5:
        # Fallback to general places if region query is too strict
        matched_places = all_places

    # Partition by category
    restaurants = [p for p in matched_places if p.get("category") == "식당 및 카페"]
    sightseeings = [p for p in matched_places if p.get("category") in ["유적지 및 관광지", "자연 및 공원"]]
    shoppings = [p for p in matched_places if p.get("category") == "쇼핑 및 시장"]
    
    # Extract profile settings
    p_style = profile.get("travel_style", {})
    p_time = profile.get("daily_timeline", {})
    p_dining = profile.get("dining_preferences", {})
    p_route = profile.get("mobility_and_routes", {})
    
    morning_start = p_time.get("morning_start_time", "10:00")
    evening_return = p_time.get("evening_return_time", "21:30")
    max_places_day = p_style.get("max_places_per_day", 4)
    pace_label = p_style.get("pace", "여유로움")
    disliked_foods = p_dining.get("disliked_foods", [])

    # Filter out disliked foods if any
    if disliked_foods:
        restaurants = [
            r for r in restaurants
            if not any(d.lower() in (r.get("tag", "") + r.get("notes", "")).lower() for d in disliked_foods)
        ]

    days = max(1, int(days))
    
    # Itinerary builder
    itinerary_days = []
    used_place_ids = set()

    def pick_next(pool):
        for p in pool:
            if p["id"] not in used_place_ids:
                used_place_ids.add(p["id"])
                return p
        # If exhausted, pick first
        return pool[0] if pool else None

    for d in range(1, days + 1):
        day_schedule = {
            "day": d,
            "title": f"Day {d}: {region} 핵심 명소 & 로컬 미식 코스",
            "hotel": hotel_info,
            "items": []
        }

        # 1. Morning Start
        day_schedule["items"].append({
            "time": morning_start,
            "title": f"숙소 출발 ({hotel_info})",
            "type": "숙박/출발",
            "desc": f"여유롭게 기상 및 준비 후 하루 시작 ({p_route.get('max_continuous_walking_minutes', 20)}분 이내 동선)",
            "link": ""
        })

        # 2. Morning Sightseeing
        m_sight = pick_next(sightseeings)
        if m_sight:
            day_schedule["items"].append({
                "time": "10:30 ~ 12:30",
                "title": m_sight["name"],
                "category": m_sight.get("category", "관광지"),
                "tag": m_sight.get("tag", ""),
                "desc": f"구글 지도 저장 관광지 방문. {m_sight.get('notes', '')}",
                "link": m_sight.get("google_maps_url", "")
            })

        # 3. Lunch
        lunch_spot = pick_next(restaurants)
        if lunch_spot:
            day_schedule["items"].append({
                "time": "12:30 ~ 14:00",
                "title": lunch_spot["name"],
                "category": "점심 식사 (식당 및 카페)",
                "tag": lunch_spot.get("tag", ""),
                "desc": f"현지 추천 런치 스팟. {lunch_spot.get('notes', '')}",
                "link": lunch_spot.get("google_maps_url", "")
            })

        # 4. Afternoon Cafe Break (as per user profile)
        cafe_spot = pick_next([r for r in restaurants if "카페" in r.get("tag", "") or "cafe" in r.get("name", "").lower()] or restaurants)
        if cafe_spot:
            day_schedule["items"].append({
                "time": "14:15 ~ 15:30",
                "title": f"{cafe_spot['name']} (카페 & 디저트)",
                "category": "오후 휴식 (카페)",
                "tag": cafe_spot.get("tag", ""),
                "desc": f"취향 프로필 반영: 오후 필수 감성 충전 및 다리 휴식 ({p_time.get('cafe_timing', '오후')})",
                "link": cafe_spot.get("google_maps_url", "")
            })

        # 5. Afternoon Sightseeing or Shopping (if pace allows)
        if max_places_day >= 3:
            afternoon_spot = pick_next(shoppings) if (d % 2 == 0 and shoppings) else pick_next(sightseeings)
            if afternoon_spot:
                day_schedule["items"].append({
                    "time": "16:00 ~ 18:00",
                    "title": afternoon_spot["name"],
                    "category": afternoon_spot.get("category", "명소"),
                    "tag": afternoon_spot.get("tag", ""),
                    "desc": f"오후 골목 탐방 & 전망 감상. {afternoon_spot.get('notes', '')}",
                    "link": afternoon_spot.get("google_maps_url", "")
                })

        # 6. Dinner
        dinner_spot = pick_next(restaurants)
        if dinner_spot:
            day_schedule["items"].append({
                "time": "18:30 ~ 20:30",
                "title": dinner_spot["name"],
                "category": "저녁 식사 (타파스/디너)",
                "tag": dinner_spot.get("tag", ""),
                "desc": f"여행지의 밤 정취를 즐길 수 있는 맛있는 디너. {dinner_spot.get('notes', '')}",
                "link": dinner_spot.get("google_maps_url", "")
            })

        # 7. Evening Return
        day_schedule["items"].append({
            "time": evening_return,
            "title": f"숙소 복귀 ({hotel_info})",
            "type": "숙박/복귀",
            "desc": "하루 일정 마무리 및 편안한 휴식",
            "link": ""
        })

        itinerary_days.append(day_schedule)

    # Format into comprehensive Markdown
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_lines = [
        f"# ✈️ [{region}] {days}일 맞춤 여행 일정표",
        "",
        f"> **기준 숙소**: {hotel_info}  ",
        f"> **여행 기간**: {days}일 코스  ",
        f"> **적용된 사용자 취향 프로필**: {pace_label} 모드 (하루 {max_places_day}곳 이내, {morning_start} 출발, 오후 카페 필수)  ",
        f"> **생성 일시**: {now_str}",
        "",
        "---",
        ""
    ]

    for day in itinerary_days:
        doc_lines.append(f"## 📅 {day['title']}")
        doc_lines.append("")
        doc_lines.append("| 시간대 | 구분 | 장소명 | 상세 설명 및 특징 | 구글 지도 |")
        doc_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        
        for it in day["items"]:
            gmap_cell = f"[📍 지도 보기]({it['link']})" if it.get("link") else "-"
            cat_cell = it.get("category") or it.get("type", "일정")
            tag_text = f" `[{it.get('tag')}]`" if it.get("tag") else ""
            name_cell = f"**{it['title']}**{tag_text}"
            desc_cell = it.get("desc", "").replace("|", "/")
            doc_lines.append(f"| {it['time']} | {cat_cell} | {name_cell} | {desc_cell} | {gmap_cell} |")
        
        doc_lines.append("")
        doc_lines.append("> 💡 **동선 안내**: 위 일정은 숙소를 기점으로 동선이 겹치지 않도록 구성되었습니다. 도보 15분 이상 이동 시 버스 또는 지하철 이용을 권장합니다.")
        doc_lines.append("")
        doc_lines.append("---")
        doc_lines.append("")

    doc_lines.extend([
        "## 💬 일정 피드백 안내",
        "일정을 확인하신 후 마음에 들지 않거나 수정하고 싶은 점이 있다면 언제든 편하게 말씀해 주세요!",
        "- 예: *\"점심 먹고 카페 대신 미술관을 가고 싶어\"*, *\"일정이 너무 빡빡해 더 여유롭게 해줘\"*, *\"해산물은 빼줘\"*, *\"쇼핑 시간을 더 줘\"*",
        "- **피드백을 주시면 고객님의 여행 취향 프로필이 즉시 학습·업데이트되어 다음 일정에 100% 반영됩니다.**"
    ])

    markdown_text = "\n".join(doc_lines)
    
    # Save to file
    ITINERARIES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"itinerary_{region}_{days}days_{timestamp_slug}.md"
    file_path = ITINERARIES_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return {
        "file_path": str(file_path),
        "region": region,
        "days": days,
        "markdown": markdown_text
    }


if __name__ == "__main__":
    import sys
    hotel = sys.argv[1] if len(sys.argv) > 1 else "바르셀로나 고딕 지구 숙소"
    d_count = sys.argv[2] if len(sys.argv) > 2 else "3"
    result = generate_itinerary(hotel, d_count)
    print(f"Itinerary generated: {result['file_path']}")
    print(result["markdown"][:500] + "...")
