#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Maps Saved Places Extractor
사용자의 모든 여행 목록에서 장소명, 카테고리(업종), 주소/위치 정보를 스크랩하여 저장합니다.
"""

import time
import json
from automate import execute_js
from test_real_click import real_click, activate_whale, get_element_coords

def goto_saved_root():
    execute_js("window.location.href = 'https://www.google.co.kr/maps/@/data=!4m2!10m1!1e1';")
    time.sleep(2.5)

def get_list_names():
    code = '''
    const rows = Array.from(document.querySelectorAll('.Io6YTe')).map(el => el.innerText.trim());
    return JSON.stringify(rows);
    '''
    return json.loads(execute_js(code))

def open_list_by_name(list_name: str) -> bool:
    print(f"📂 목록 여는 중: [{list_name}]...")
    coords = get_element_coords(list_name)
    if not coords:
        print(f"❌ [{list_name}] 좌표를 찾을 수 없습니다.")
        return False
    
    activate_whale()
    time.sleep(0.2)
    real_click(coords['x'], coords['y'])
    time.sleep(2.5)
    return True

def scroll_and_extract_places(list_name: str):
    print(f"📜 [{list_name}] 장소 목록 스크롤 및 추출 시작...")
    
    # 1. 스크롤하여 모든 장소 로드
    scroll_code = '''
    const scrollEl = document.querySelector('div[role="feed"], div.m6QErb[aria-label], div.m6QErb');
    if (scrollEl) {
        scrollEl.scrollTop = scrollEl.scrollHeight;
        return scrollEl.scrollHeight;
    }
    return 0;
    '''
    for _ in range(8):
        execute_js(scroll_code)
        time.sleep(0.6)

    # 2. 장소 카드 데이터 추출
    extract_code = f'''
    const cards = Array.from(document.querySelectorAll('.SMP2wb, div[role="article"]')).filter(c => {{
        return c.innerText && c.innerText.length > 0;
    }});

    const results = [];
    for (const card of cards) {{
        const titleEl = card.querySelector('.fontHeadlineSmall') || card.querySelector('h2');
        const title = titleEl ? titleEl.innerText.trim() : null;
        if (!title) continue;

        // 태그/업종 텍스트 추출
        const spans = Array.from(card.querySelectorAll('span, .fontBodyMedium'));
        let subText = "";
        for (const span of spans) {{
            const t = span.innerText.trim();
            if (t && !t.includes('★') && !t.match(/^\\d+(\\.\\d+)?$/) && !t.includes('(') && t.length < 35 && t !== title) {{
                subText = t.replace(/^[·\\s]+/, '');
                break;
            }}
        }}

        results.push({{
            listName: "{list_name}",
            name: title,
            tag: subText,
            fullCardText: card.innerText
        }});
    }}
    return JSON.stringify(results);
    '''
    raw = execute_js(extract_code)
    try:
        places = json.loads(raw)
        # Deduplicate
        seen = set()
        unique = []
        for p in places:
            if p['name'] not in seen:
                seen.add(p['name'])
                unique.append(p)
        print(f"  ➔ [{list_name}]에서 {len(unique)}개 장소 수집 완료!")
        return unique
    except Exception as e:
        print(f"❌ 파싱 오류: {e}")
        return []

def main():
    print("🚀 구글 지도 저장함 전체 장소 수집을 시작합니다...")
    goto_saved_root()
    
    lists = get_list_names()
    print("📋 발견된 목록들:", lists)

    # 대상 여행 목록들 필터링
    target_lists = [
        "2026 스페인 포르토 여행",
        "2026 이탈리아 프랑스 여행",
        "2026 대만",
        "대만 식당",
        "여행 계획"
    ]
    
    all_places = []
    for list_name in target_lists:
        if list_name in lists:
            if open_list_by_name(list_name):
                places = scroll_and_extract_places(list_name)
                all_places.extend(places)
                goto_saved_root()
        else:
            print(f"⚠️ [{list_name}]이 화면 목록에 보이지 않습니다.")

    print(f"\n✨ 총 {len(all_places)}개의 장소를 성공적으로 수집했습니다!")
    with open("extracted_places.json", "w", encoding="utf-8") as f:
        json.dump(all_places, f, ensure_ascii=False, indent=2)
    print("💾 'extracted_places.json'에 저장 완료!")

if __name__ == "__main__":
    main()
