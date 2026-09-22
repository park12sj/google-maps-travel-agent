#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup all original lists and places to local history files (JSON and Markdown).
"""

import json
from datetime import datetime
from pathlib import Path

# Load all places
with open('extracted_places.json', 'r', encoding='utf-8') as f:
    extracted = json.load(f)

with open('spain_44_places.json', 'r', encoding='utf-8') as f:
    spain = json.load(f)

with open('travel_plan_places.json', 'r', encoding='utf-8') as f:
    travel_plan = json.load(f)

history = {
    "backup_timestamp": datetime.now().isoformat(),
    "description": "구글 지도 저장함 원본 여행 목록 히스토리 백업",
    "lists": {
        "2026 스페인 포르토 여행": spain,
        "2026 이탈리아 프랑스 여행": [p for p in extracted if p.get('listName') == '2026 이탈리아 프랑스 여행'],
        "2026 대만": [p for p in extracted if p.get('listName') == '2026 대만'],
        "대만 식당": [p for p in extracted if p.get('listName') == '대만 식당'],
        "여행 계획": travel_plan,
        "즐겨찾기": ["La Pecora Pazza", "Mr.Clood Bistrot", "Pizza 4P’s Bao Khanh"],
        "가고 싶은 장소": ["Lai Heen"],
        "Saved places": ["Via Stefano Canzio, 6"]
    }
}

# Write JSON backup
with open('history_backup_all_original_lists.json', 'w', encoding='utf-8') as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# Write Markdown backup
md_lines = [
    "# 📍 구글 지도 원본 여행 목록 히스토리 백업 (Local History Archive)",
    f"\n> **백업 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "> **안내**: 구글 지도 저장함에서 삭제된 원본 여행 목록들의 장소 정보가 본 문서에 영구 보존됩니다.\n",
    "---\n"
]

for list_name, items in history["lists"].items():
    md_lines.append(f"## 📁 {list_name} ({len(items)}개 장소)")
    if not items:
        md_lines.append("*(장소 없음)*\n")
        continue
        
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            name = item.get('name') or item.get('title')
            tag = item.get('tag', '')
            full = item.get('fullText') or item.get('fullCardText', '')
            tag_str = f" `{tag}`" if tag else ""
            md_lines.append(f"{i}. **{name}**{tag_str}")
            if full and full != name:
                sub_lines = [l.strip() for l in full.split('\n') if l.strip() and l.strip() != name]
                if sub_lines:
                    md_lines.append(f"   - 상세: {', '.join(sub_lines)}")
        else:
            md_lines.append(f"{i}. **{item}**")
    md_lines.append("\n---\n")

with open('history_backup_all_original_lists.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print("✅ 로컬 히스토리 백업 파일 생성 완료:")
print("   - history_backup_all_original_lists.json")
print("   - history_backup_all_original_lists.md")
