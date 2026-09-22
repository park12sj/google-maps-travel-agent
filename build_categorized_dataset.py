#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build final consolidated categorized dataset of all user's places.
"""

import json
from pathlib import Path

# Load spain 44 places
with open('spain_44_places.json', 'r', encoding='utf-8') as f:
    spain = json.load(f)

# Load other extracted places
with open('extracted_places.json', 'r', encoding='utf-8') as f:
    extracted = json.load(f)

all_items = {}

for item in spain:
    name = item['name']
    all_items[name] = {
        'name': name,
        'tag': item.get('tag', ''),
        'source': '2026 스페인 포르토 여행'
    }

for item in extracted:
    name = item['name']
    if name not in all_items:
        all_items[name] = {
            'name': name,
            'tag': item.get('tag', ''),
            'source': item.get('listName', '')
        }

# Add remaining specific places from other lists
extra_places = [
    {'name': 'Pizza 4P’s Bao Khanh', 'tag': '피자 레스토랑', 'source': '즐겨찾기'},
    {'name': 'Lai Heen', 'tag': '미슐랭 광둥 요리', 'source': '가고 싶은 장소'},
    {'name': '古民家「禅」', 'tag': '전통 숙소', 'source': '여행 계획'},
    {'name': '무사시노 산토리 맥주공장', 'tag': '맥주 브루어리', 'source': '여행 계획'},
    {'name': '워너 브라더스 스튜디오 투어 도쿄 - 메이킹 오브 해리 포터', 'tag': '테마 명소', 'source': '여행 계획'},
    {'name': '팀랩 플래닛 도쿄', 'tag': '디지털 아트 전시관', 'source': '여행 계획'}
]

for item in extra_places:
    name = item['name']
    if name not in all_items:
        all_items[name] = item

def categorize(item):
    name = item['name']
    tag = item.get('tag', '')
    combined = f"{name} {tag}".lower()

    # 1. 숙박
    if any(k in combined for k in ['호텔', 'hotel', '숙소', 'resort', '호스텔', '비앤비', '민박', 'posada', '禅', 'via stefano canzio']):
        return '숙박'

    # 2. 식당 및 카페
    if any(k in combined for k in [
        '타파스', '칵테일', '요리', '음식점', '레스토랑', '비스트로', '식당', '카페', 'cafe', 'bar',
        'blai', 'vinitus', '시우다드 콘달', 'meia-nau', 'vinhas', 'fernandes', 'cantina 32',
        '보아 노바', '참피뇬', 'salesas', 'oink', 'frog', 'pecora pazza', 'clood', '레이허우',
        '은하동', '키키', 'pizza', 'lai heen', '맥주공장', '포차', 'bocadillos'
    ]):
        return '식당 및 카페'

    # 3. 쇼핑 및 시장
    if any(k in combined for k in ['시장', 'market', 'rastro', '쇼핑']):
        return '쇼핑 및 시장'

    # 4. 자연 및 공원
    if any(k in combined for k in ['해변', '명승지', '만/포구', '정원', '공원', '식물원', 'cala', 'caló', '동물원', '지질공원', 'sa calobra']):
        return '자연 및 공원'

    # 5. 유적지 및 관광지
    return '유적지 및 관광지'

categorized_groups = {
    '식당 및 카페': [],
    '숙박': [],
    '유적지 및 관광지': [],
    '자연 및 공원': [],
    '쇼핑 및 시장': []
}

flat_list = []

for name, item in all_items.items():
    cat = categorize(item)
    item['targetCategory'] = cat
    categorized_groups[cat].append(item)
    flat_list.append(item)

print("=" * 60)
print(f"📊 총 {len(flat_list)}개 장소 분류 완료:")
print("=" * 60)
for cat, items in categorized_groups.items():
    print(f"  • {cat:15s} : {len(items):2d}개 장소")
print("=" * 60)

with open('final_categorized_places.json', 'w', encoding='utf-8') as f:
    json.dump(flat_list, f, ensure_ascii=False, indent=2)

print("\n💾 'final_categorized_places.json'에 저장 완료!")
