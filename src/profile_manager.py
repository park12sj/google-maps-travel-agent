#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profile Manager Module.
Analyzes user feedback, dynamically adapts travel preferences,
and updates both JSON and Markdown profile configurations.
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
PROFILE_JSON_PATH = CONFIG_DIR / "user_travel_profile.json"
PROFILE_MD_PATH = CONFIG_DIR / "user_travel_profile.md"


def load_profile():
    """Load current user travel profile."""
    if not PROFILE_JSON_PATH.exists():
        return get_default_profile()
    with open(PROFILE_JSON_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return get_default_profile()


def get_default_profile():
    return {
        "profile_version": "1.0.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "travel_style": {
            "pace": "여유로움",
            "description": "핵심 장소 위주로 머무르고 충분히 휴식하는 스타일",
            "max_places_per_day": 4,
            "recommended_duration_per_spot": {
                "식당": "60~90분",
                "카페": "60~90분 (휴식 겸 분위기)",
                "관광지_유적지": "90~120분",
                "공원_자연": "60~90분",
                "쇼핑_시장": "60~90분"
            }
        },
        "daily_timeline": {
            "morning_start_time": "10:00",
            "evening_return_time": "21:30",
            "must_include_cafe_break": True,
            "cafe_timing": "점심 식사 후 (14:00 ~ 15:30 사이)"
        },
        "dining_preferences": {
            "vibe": ["현지 로컬 맛집", "감성 카페", "뷰가 좋은 곳"],
            "meal_patterns": {
                "lunch": "일정 동선 상의 편안한 로컬 맛집",
                "cafe": "채광 좋고 감성적인 휴식 공간",
                "dinner": "여행지의 정취를 즐길 수 있는 맛있는 디너 / 타파스 / 로컬 주점"
            },
            "dietary_restrictions": [],
            "disliked_foods": []
        },
        "mobility_and_routes": {
            "preferred_transit": ["도보 15분 이내", "지하철/버스 편리한 동선", "먼 거리는 택시"],
            "max_continuous_walking_minutes": 20,
            "clustering_rule": "하루 일정은 동일 권역/도보권 내로 묶어 지그재그 이동 배제"
        },
        "interests_and_priorities": {
            "high_priority": ["분위기 좋은 카페", "로컬 맛집", "탁 트인 전망/경치"],
            "medium_priority": ["소품샵/시장 둘러보기", "공원 산책"],
            "low_priority": ["과도하게 긴 대기열의 관광지", "지나치게 상업화된 투어 코스"]
        },
        "feedback_history": []
    }


def analyze_feedback(feedback_text, current_profile):
    """
    Analyze user feedback text and extract adjustments to travel style.
    Returns (updated_profile, list_of_changes).
    """
    text = feedback_text.lower()
    changes = []
    
    # 1. Pace / Intensity
    if any(k in text for k in ["빡빡", "힘들", "피곤", "여유롭", "줄여", "지쳐", "바빠"]):
        current_profile["travel_style"]["pace"] = "매우 여유로움"
        current_profile["travel_style"]["max_places_per_day"] = max(2, current_profile["travel_style"]["max_places_per_day"] - 1)
        changes.append(f"여행 템포를 '매우 여유로움'으로 완화 (하루 최대 장소 수: {current_profile['travel_style']['max_places_per_day']}개)")
    elif any(k in text for k in ["알차게", "더 많이", "비어있", "심심", "타이트", "꽉 차"]):
        current_profile["travel_style"]["pace"] = "알찬 탐방형"
        current_profile["travel_style"]["max_places_per_day"] = min(6, current_profile["travel_style"]["max_places_per_day"] + 1)
        changes.append(f"여행 템포를 '알찬 탐방형'으로 확대 (하루 최대 장소 수: {current_profile['travel_style']['max_places_per_day']}개)")

    # 2. Morning / Schedule start
    if any(k in text for k in ["아침잠", "늦잠", "11시", "12시", "늦게 시작"]):
        current_profile["daily_timeline"]["morning_start_time"] = "11:00"
        changes.append("일정 시작 시간을 11:00으로 늦춤 (여유로운 아침 보장)")
    elif any(k in text for k in ["일찍", "오전 8시", "오전 9시", "조식"]):
        current_profile["daily_timeline"]["morning_start_time"] = "09:00"
        changes.append("일정 시작 시간을 09:00으로 당김")

    # 3. Walking / Transit
    if any(k in text for k in ["걷기 싫", "다리 아파", "도보 줄여", "택시", "많이 걷", "도보도", "도보 10분", "힘드니까", "도보"]):
        current_profile["mobility_and_routes"]["max_continuous_walking_minutes"] = 10
        if "택시 우선" not in current_profile["mobility_and_routes"]["preferred_transit"]:
            current_profile["mobility_and_routes"]["preferred_transit"].insert(0, "택시 우선")
        changes.append("최대 도보 시간을 10분으로 축소하고 택시/단거리 이동 선호 반영")
    elif any(k in text for k in ["산책 좋아", "걷는 거 좋아", "골목 걷기", "도보 좋아"]):
        current_profile["mobility_and_routes"]["max_continuous_walking_minutes"] = 30
        changes.append("도보 산책 친화 성향 반영 (최대 연속 도보 30분 허용)")

    # 4. Cafe & Dessert
    if any(k in text for k in ["카페 더", "카페 2번", "커피 필수", "디저트", "카페 가고"]):
        current_profile["daily_timeline"]["must_include_cafe_break"] = True
        current_profile["daily_timeline"]["cafe_timing"] = "하루 2회 (오후 1회 + 저녁 또는 오전 1회)"
        if "감성 카페 투어" not in current_profile["interests_and_priorities"]["high_priority"]:
            current_profile["interests_and_priorities"]["high_priority"].insert(0, "감성 카페 투어")
        changes.append("카페 비중 대폭 상향 (하루 2회 카페 방문 & 감성 카페 우선순위 최상향)")

    # 5. Food preferences & Restrictions
    if any(k in text for k in ["해산물", "비린", "스시 싫", "회 싫"]):
        if "해산물" not in current_profile["dining_preferences"]["disliked_foods"]:
            current_profile["dining_preferences"]["disliked_foods"].append("해산물")
            changes.append("기피 음식에 '해산물' 등록 (고기/타파스/양식 위주로 추천)")
    if any(k in text for k in ["고기", "스테이크", "육류"]):
        if "고기/스테이크 맛집" not in current_profile["dining_preferences"]["vibe"]:
            current_profile["dining_preferences"]["vibe"].append("고기/스테이크 맛집")
            changes.append("미식 취향에 '고기/스테이크' 추가")
    if any(k in text for k in ["가성비", "저렴"]):
        current_profile["dining_preferences"]["vibe"].append("가성비 로컬 맛집")
        changes.append("미식 성향에 '가성비 로컬 맛집' 반영")
    if any(k in text for k in ["파인다이닝", "고급", "미슐랭", "분위기 끝판왕"]):
        current_profile["dining_preferences"]["vibe"].append("파인다이닝/미슐랭/고급 레스토랑")
        changes.append("미식 성향에 '파인다이닝/미슐랭/고급 레스토랑' 반영")

    # 6. Activities & Interests
    if any(k in text for k in ["쇼핑", "소품샵", "마켓", "시장"]):
        if "쇼핑/시장 탐방" not in current_profile["interests_and_priorities"]["high_priority"]:
            current_profile["interests_and_priorities"]["high_priority"].append("쇼핑/시장 탐방")
            changes.append("관심사에 '쇼핑/시장 탐방' 최우선 순위 등록")
    if any(k in text for k in ["유적지 지루", "박물관 싫", "역사 빼"]):
        if "박물관/역사 유적" not in current_profile["interests_and_priorities"]["low_priority"]:
            current_profile["interests_and_priorities"]["low_priority"].append("박물관/역사 유적")
            changes.append("기피 관심사에 '박물관/역사 유적' 등록")
    if any(k in text for k in ["자연", "바다", "해변", "공원", "힐링"]):
        if "자연 및 힐링 명소" not in current_profile["interests_and_priorities"]["high_priority"]:
            current_profile["interests_and_priorities"]["high_priority"].append("자연 및 힐링 명소")
            changes.append("관심사에 '자연 및 힐링 명소' 최우선 순위 등록")

    # If no specific rule triggered, record generic learning
    if not changes:
        changes.append(f"피드백 반영: '{feedback_text.strip()}' (개인 선호 지침에 기록)")

    return current_profile, changes


def update_profile_with_feedback(feedback_text):
    """
    Main entrypoint: analyzes feedback, updates user_travel_profile.json,
    and regenerates user_travel_profile.md.
    """
    profile = load_profile()
    updated_profile, changes = analyze_feedback(feedback_text, profile)
    
    # Update metadata
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_profile["last_updated"] = now_str
    
    # Append to history
    updated_profile.setdefault("feedback_history", []).append({
        "timestamp": now_str,
        "feedback": feedback_text,
        "applied_changes": changes
    })

    # Save JSON
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_profile, f, ensure_ascii=False, indent=2)

    # Regenerate Markdown
    generate_profile_markdown(updated_profile)

    return {
        "status": "success",
        "timestamp": now_str,
        "changes": changes,
        "current_pace": updated_profile["travel_style"]["pace"],
        "max_places_per_day": updated_profile["travel_style"]["max_places_per_day"],
        "morning_start_time": updated_profile["daily_timeline"]["morning_start_time"]
    }


def generate_profile_markdown(profile):
    """Generates user_travel_profile.md from profile dict."""
    p_style = profile.get("travel_style", {})
    p_time = profile.get("daily_timeline", {})
    p_dining = profile.get("dining_preferences", {})
    p_route = profile.get("mobility_and_routes", {})
    p_inter = profile.get("interests_and_priorities", {})
    p_hist = profile.get("feedback_history", [])

    lines = [
        "# 🧭 사용자 맞춤 여행 스타일 프로필 (User Travel Profile)",
        "",
        f"> **상태**: 활성화됨 (에이전트가 일정 생성 시 자동 100% 참조)  ",
        f"> **마지막 업데이트**: {profile.get('last_updated')}  ",
        f"> **프로필 버전**: {profile.get('profile_version', '1.0.0')}",
        "",
        "---",
        "",
        "## 1. 여행 템포 & 스케줄 (Pace & Schedule)",
        f"- **기본 템포**: **{p_style.get('pace', '여유로움')}**",
        f"  - 설명: {p_style.get('description', '')}",
        f"- **하루 권장 방문 장소 수**: **최대 {p_style.get('max_places_per_day', 4)}곳**",
        f"- **일정 시작 시간**: **{p_time.get('morning_start_time', '10:00')} AM**",
        f"- **숙소 복귀 시간**: **{p_time.get('evening_return_time', '21:30')} PM** 내외",
        f"- **카페 휴식**: **{p_time.get('cafe_timing', '오후 필수')}**",
        "",
        "---",
        "",
        "## 2. 미식 & 카페 취향 (Dining & Cafe)",
        f"- **식당/카페 바이브**: {', '.join(p_dining.get('vibe', []))}",
        f"- **점심**: {p_dining.get('meal_patterns', {}).get('lunch', '')}",
        f"- **카페**: {p_dining.get('meal_patterns', {}).get('cafe', '')}",
        f"- **저녁**: {p_dining.get('meal_patterns', {}).get('dinner', '')}",
    ]

    disliked = p_dining.get("disliked_foods", [])
    if disliked:
        lines.append(f"- ⚠️ **기피/제외 음식**: **{', '.join(disliked)}** (절대 추천 금지)")

    lines.extend([
        "",
        "---",
        "",
        "## 3. 이동 & 동선 (Mobility & Route)",
        f"- **선호 이동 수단**: {', '.join(p_route.get('preferred_transit', []))}",
        f"- **최대 연속 도보 한계**: **{p_route.get('max_continuous_walking_minutes', 20)}분 이내**",
        f"- **동선 원칙**: **{p_route.get('clustering_rule', '동일 권역 클러스터링')}**",
        "",
        "---",
        "",
        "## 4. 관심사 및 우선순위 (Priorities)",
        f"- 🌟 **최우선 선호**: {', '.join(p_inter.get('high_priority', []))}",
        f"- 🌿 **보통 관심**: {', '.join(p_inter.get('medium_priority', []))}",
        f"- 🚫 **기피/비선호**: {', '.join(p_inter.get('low_priority', []))}",
        "",
        "---",
        "",
        "## 5. 피드백 누적 학습 히스토리 (Feedback History)",
    ])

    for item in reversed(p_hist[-10:]):  # show last 10 entries
        lines.append(f"- **[{item.get('timestamp')}]** 피드백: \"{item.get('feedback')}\"")
        for chg in item.get("applied_changes", []):
            lines.append(f"  - ↳ {chg}")

    lines.append("")

    with open(PROFILE_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_feedback = " ".join(sys.argv[1:])
        res = update_profile_with_feedback(test_feedback)
        print("Updated successfully:")
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("Usage: python3 profile_manager.py '<feedback text>'")
