#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Google My Maps import files (CSV and KML) with predefined colors and icons.
"""

import json
import csv
from pathlib import Path

with open('final_categorized_places.json', 'r', encoding='utf-8') as f:
    places = json.load(f)

# Group by category
grouped = {}
for p in places:
    cat = p['targetCategory']
    grouped.setdefault(cat, []).append(p)

category_styles = {
    "식당 및 카페": {"color": "#FF5252", "color_name": "빨간색 (Red)", "icon": "restaurant"},
    "숙박": {"color": "#448AFF", "color_name": "파란색 (Blue)", "icon": "lodging"},
    "유적지 및 관광지": {"color": "#FFD700", "color_name": "노란색/금색 (Yellow)", "icon": "monument"},
    "자연 및 공원": {"color": "#4CAF50", "color_name": "초록색 (Green)", "icon": "tree"},
    "쇼핑 및 시장": {"color": "#AB47BC", "color_name": "보라색 (Purple)", "icon": "shopping"}
}

output_dir = Path("mymaps_bundle")
output_dir.mkdir(exist_ok=True)

for cat, items in grouped.items():
    style = category_styles.get(cat, {"color": "#9E9E9E", "color_name": "회색"})
    safe_name = cat.replace(" ", "_")
    csv_path = output_dir / f"내지도_{safe_name}.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["장소명", "카테고리", "권장색상", "원본목록", "태그"])
        for item in items:
            writer.writerow([
                item['name'],
                cat,
                style["color_name"],
                item.get('source', ''),
                item.get('tag', '')
            ])

print("✅ 구글 내 지도(My Maps) 레이어별 CSV 파일 생성 완료: mymaps_bundle/")
for cat in grouped:
    style = category_styles.get(cat, {})
    print(f"  • {cat} ({len(grouped[cat])}개 장소) -> 권장 색상: {style.get('color_name')}")
