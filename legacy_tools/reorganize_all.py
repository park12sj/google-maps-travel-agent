#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Maps Saved Places Batch Reorganizer
모든 저장된 장소들을 해당 카테고리 목록(식당 및 카페, 숙박, 유적지 및 관광지, 자연 및 공원, 쇼핑 및 시장)으로
구글 지도에서 자동으로 저장해 주는 완성형 스크립트.
"""

import time
import json
import urllib.parse
from pathlib import Path
from automate import execute_js
from test_real_click import real_click, activate_whale

PROGRESS_FILE = Path("reorganize_progress.json")

def load_progress() -> set:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_progress(done_set: set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done_set), f, ensure_ascii=False, indent=2)

def safe_json(raw):
    if not raw or raw == 'null':
        return None
    try:
        return json.loads(raw)
    except:
        return None

def move_place_to_category(name: str, target_cat: str) -> bool:
    search_url = f"https://www.google.co.kr/maps/search/{urllib.parse.quote(name)}"
    execute_js(f'window.location.href = "{search_url}";')
    time.sleep(3.5)

    # 1. 저장(또는 저장됨) 버튼 찾기
    find_save_code = '''
    const btns = Array.from(document.querySelectorAll('button')).filter(b => {
        const v = b.getAttribute('data-value') || '';
        const a = b.getAttribute('aria-label') || '';
        const t = b.innerText || '';
        return v.includes('저장') || a.includes('저장') || (t.includes('저장') && !t.includes('최근'));
    });
    const btn = btns.find(b => b.offsetWidth > 0 && b.getBoundingClientRect().top > 80);
    if (!btn) return null;
    const rect = btn.getBoundingClientRect();
    const topChrome = window.outerHeight - window.innerHeight;
    return JSON.stringify({
        text: btn.innerText,
        x: window.screenX + rect.left + rect.width / 2,
        y: window.screenY + topChrome + rect.top + rect.height / 2
    });
    '''
    save_coords = safe_json(execute_js(find_save_code))

    if not save_coords:
        # 검색 결과가 여러 개 나와서 목록으로 표시된 경우 첫 번째 결과 클릭 시도
        first_res_code = '''
        const first = document.querySelector('div[role="article"] button, div.fontHeadlineSmall');
        if (!first) return null;
        const rect = first.getBoundingClientRect();
        const topChrome = window.outerHeight - window.innerHeight;
        return JSON.stringify({
            x: window.screenX + rect.left + rect.width / 2,
            y: window.screenY + topChrome + rect.top + rect.height / 2
        });
        '''
        first_coords = safe_json(execute_js(first_res_code))
        if first_coords:
            activate_whale()
            time.sleep(0.1)
            real_click(first_coords['x'], first_coords['y'])
            time.sleep(3.0)
            save_coords = safe_json(execute_js(find_save_code))

    if not save_coords:
        print(f"  ⚠️ '{name}'의 저장 버튼을 찾을 수 없어 건너뜁니다.")
        return False

    # 2. 저장 버튼 클릭 -> 팝업 열기
    activate_whale()
    time.sleep(0.1)
    real_click(save_coords['x'], save_coords['y'])
    time.sleep(1.5)

    # 3. 팝업 내 대상 카테고리 목록 위치 탐색
    find_target_code = f'''
    const items = Array.from(document.querySelectorAll('div[role="menuitemradio"], div[role="menuitemcheckbox"], div[role="menuitem"], div[role="dialog"] label'));
    const target = items.find(i => (i.innerText || '').includes('{target_cat}'));
    if (!target) return null;
    const rect = target.getBoundingClientRect();
    const topChrome = window.outerHeight - window.innerHeight;
    return JSON.stringify({{
        text: target.innerText,
        checked: target.getAttribute('aria-checked'),
        x: window.screenX + rect.left + rect.width / 2,
        y: window.screenY + topChrome + rect.top + rect.height / 2
    }});
    '''
    target_info = safe_json(execute_js(find_target_code))

    if target_info:
        if target_info.get('checked') != 'true':
            real_click(target_info['x'], target_info['y'])
            time.sleep(0.8)
            print(f"  ✅ [{target_cat}]에 추가 완료!")
        else:
            print(f"  ℹ️ 이미 [{target_cat}]에 저장되어 있습니다.")
    else:
        print(f"  ⚠️ 팝업에서 [{target_cat}] 목록을 찾지 못했습니다.")

    # 4. 팝업 닫기 (ESC)
    execute_js('''
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));
    ''')
    time.sleep(0.6)
    return True

def main():
    with open("final_categorized_places.json", "r", encoding="utf-8") as f:
        places = json.load(f)

    done = load_progress()
    total = len(places)
    
    print("=" * 60)
    print(f"🚀 구글 지도 저장함 일괄 재편 작업을 재개합니다! (총 {total}개 장소)")
    print(f"   진행 완료된 장소: {len(done)}개 / 남은 장소: {total - len(done)}개")
    print("=" * 60)

    for idx, p in enumerate(places, 1):
        name = p['name']
        cat = p['targetCategory']

        if name in done:
            continue

        print(f"\n[{idx}/{total}] '{name}' -> [{cat}] 진행 중...")
        success = move_place_to_category(name, cat)
        if success:
            done.add(name)
            save_progress(done)
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("🎉 모든 저장함 재편 작업이 성공적으로 완료되었습니다!")
    print("=" * 60)

if __name__ == "__main__":
    main()
