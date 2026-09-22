#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage Module for Google Maps Saved Places.
Handles reading/writing master places database and syncing MyMaps CSV bundles.
"""

import os
import json
import csv
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PLACES_MASTER_PATH = DATA_DIR / "places" / "places_master.json"
MYMAPS_DIR = DATA_DIR / "mymaps"

# Canonical Category Definitions
CATEGORIES = [
    "식당 및 카페",
    "숙박",
    "유적지 및 관광지",
    "자연 및 공원",
    "쇼핑 및 시장",
    "기타"
]

CATEGORY_FILE_MAP = {
    "식당 및 카페": "내지도_식당_및_카페.csv",
    "숙박": "내지도_숙박.csv",
    "유적지 및 관광지": "내지도_유적지_및_관광지.csv",
    "자연 및 공원": "내지도_자연_및_공원.csv",
    "쇼핑 및 시장": "내지도_쇼핑_및_시장.csv",
    "기타": "내지도_기타.csv"
}


def load_places():
    """Load all places from master database."""
    if not PLACES_MASTER_PATH.exists():
        return []
    with open(PLACES_MASTER_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_places(places, auto_push=True):
    """Save places list to master database, auto-sync MyMaps CSVs, and push to remote git."""
    PLACES_MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLACES_MASTER_PATH, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
    sync_mymaps_csvs(places)
    
    if auto_push:
        try:
            from .git_sync import git_auto_push
            git_auto_push(f"feat(places): 장소 DB 및 MyMaps CSV 자동 동기화 ({len(places)}곳)")
        except Exception:
            pass


def add_place(name, category, tag="", region="", notes="", source_url="", google_maps_url=None, auto_push=True):
    """
    Add a new place to master database (with duplicate check).
    Returns (created_place, is_duplicate).
    """
    places = load_places()
    name = name.strip()
    
    # Check if place already exists
    for p in places:
        if p["name"].lower() == name.lower():
            # Update notes or source or maps url if new info
            if source_url and source_url not in p.get("original_source", ""):
                p["original_source"] = f"{p.get('original_source', '')}, {source_url}".strip(", ")
            if notes and notes not in p.get("notes", ""):
                p["notes"] = f"{p.get('notes', '')} | {notes}".strip(" |")
            if google_maps_url and ("search/?api=1" in p.get("google_maps_url", "") or not p.get("google_maps_url")):
                p["google_maps_url"] = google_maps_url
            save_places(places, auto_push=auto_push)
            return p, True

    # Assign new ID
    next_num = len(places) + 1
    new_id = f"place_{next_num:03d}"
    
    # Validate category
    if category not in CATEGORIES:
        category = "기타"

    if not google_maps_url:
        search_query = f"{name} {region}".strip() if region and region != "미지정" else name
        encoded_query = quote(search_query)
        google_maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

    new_place = {
        "id": new_id,
        "name": name,
        "category": category,
        "tag": tag,
        "region": region or "미지정",
        "original_source": source_url or "사용자 추가",
        "google_maps_url": google_maps_url,
        "notes": notes,
        "added_at": datetime.now().isoformat(timespec="seconds")
    }

    places.append(new_place)
    save_places(places, auto_push=auto_push)
    return new_place, False


def find_places_by_region_or_query(query=""):
    """Find places matching region, tag, or name."""
    places = load_places()
    if not query:
        return places
    
    q = query.lower()
    return [
        p for p in places
        if q in p.get("region", "").lower()
        or q in p.get("name", "").lower()
        or q in p.get("tag", "").lower()
        or q in p.get("notes", "").lower()
        or q in p.get("original_source", "").lower()
    ]


def sanitize_region_name(region):
    """Sanitize region name for safe filesystem directory and file names."""
    if not region or not str(region).strip() or str(region).strip() in ["미지정", "기타"]:
        return "기타"
    cleaned = re.sub(r'[\\/*?:"<>|]', '_', str(region).strip())
    cleaned = cleaned.strip(". ")
    return cleaned or "기타"


def get_available_regions():
    """Return sorted list of unique sanitized region names in master database."""
    places = load_places()
    regions = set(sanitize_region_name(p.get("region")) for p in places)
    return sorted(list(regions))


def load_places_by_region(region_name):
    """Load places belonging to a specific region (matches exact or sanitized name)."""
    places = load_places()
    target = sanitize_region_name(region_name).lower()
    return [
        p for p in places
        if sanitize_region_name(p.get("region")).lower() == target
        or target in p.get("region", "").lower()
    ]


def sync_mymaps_csvs(places=None):
    """
    Regenerate CSV files in data/mymaps/ partitioned by region and canonical categories.
    Structure:
      - data/mymaps/{region}/내지도_{카테고리}.csv (지역별 카테고리 분리 파일)
      - data/mymaps/{region}/{region}_전체.csv (해당 지역 모든 장소 단일 레이어용)
      - data/mymaps/_전체_통합/내지도_{카테고리}.csv & 전체_장소_통합.csv
      - data/mymaps/내지도_{카테고리}.csv (루트 단일 통합 유지로 상위 호환성 보장)
    """
    if places is None:
        places = load_places()

    MYMAPS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = ["장소 이름", "검색위치", "카테고리", "세부 태그/설명", "지역", "구글 지도 링크", "출처"]

    def _write_csv(filepath, items):
        if not items:
            return
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for it in items:
                name = it.get("name", "")
                region = it.get("region", "")
                clean_name = name.split(" / ")[0].split("(")[0].strip()
                search_loc = f"{clean_name} {region}".strip() if region and region != "미지정" else clean_name
                
                writer.writerow({
                    "장소 이름": name,
                    "검색위치": search_loc,
                    "카테고리": it.get("category", ""),
                    "세부 태그/설명": it.get("tag", "") or it.get("notes", ""),
                    "지역": region,
                    "구글 지도 링크": it.get("google_maps_url", ""),
                    "출처": it.get("original_source", "")
                })

    # 1. Group places by sanitized region
    regions_map = {}
    for p in places:
        reg_key = sanitize_region_name(p.get("region"))
        regions_map.setdefault(reg_key, []).append(p)

    summary = {
        "total_places": len(places),
        "regions": {}
    }

    # 2. Generate region-specific CSV files in data/mymaps/{region}/
    for reg_name, reg_places in regions_map.items():
        reg_dir = MYMAPS_DIR / reg_name
        reg_dir.mkdir(parents=True, exist_ok=True)

        reg_cat_counts = {}
        for cat in CATEGORIES:
            cat_places = [p for p in reg_places if p.get("category", "기타") == cat]
            if cat_places:
                filename = CATEGORY_FILE_MAP.get(cat, f"내지도_{cat}.csv")
                _write_csv(reg_dir / filename, cat_places)
                reg_cat_counts[cat] = len(cat_places)

        # Region full places CSV
        all_reg_filename = f"{reg_name}_전체.csv"
        _write_csv(reg_dir / all_reg_filename, reg_places)

        summary["regions"][reg_name] = {
            "count": len(reg_places),
            "categories": reg_cat_counts,
            "dir": str(reg_dir)
        }

    # 3. Generate unified CSV bundles (_전체_통합 and root data/mymaps/ for backward compatibility)
    unified_dir = MYMAPS_DIR / "_전체_통합"
    unified_dir.mkdir(parents=True, exist_ok=True)

    for cat in CATEGORIES:
        cat_places = [p for p in places if p.get("category", "기타") == cat]
        filename = CATEGORY_FILE_MAP.get(cat, f"내지도_{cat}.csv")
        # Write to _전체_통합
        _write_csv(unified_dir / filename, cat_places)
        # Write to root data/mymaps/
        _write_csv(MYMAPS_DIR / filename, cat_places)

    _write_csv(unified_dir / "전체_장소_통합.csv", places)

    return summary


if __name__ == "__main__":
    places = load_places()
    print(f"Loaded {len(places)} places from storage.")
    res = sync_mymaps_csvs(places)
    print(f"MyMaps sync complete: {len(res['regions'])} regions processed.")
