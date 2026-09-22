#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage Module for Google Maps Saved Places.
Handles reading/writing master places database and syncing MyMaps CSV bundles.
"""

import os
import json
import csv
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


def save_places(places):
    """Save places list to master database and auto-sync MyMaps CSVs."""
    PLACES_MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLACES_MASTER_PATH, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
    sync_mymaps_csvs(places)


def add_place(name, category, tag="", region="", notes="", source_url="", google_maps_url=None):
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
            save_places(places)
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
    save_places(places)
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


def sync_mymaps_csvs(places=None):
    """
    Regenerate CSV files in data/mymaps/ partitioned strictly by the canonical 6 categories.
    All places regardless of region are accumulated into these unified files.
    Any rogue or regional CSV files (e.g. 후쿠오카_*.csv) are purged.
    """
    if places is None:
        places = load_places()

    MYMAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Strictly purge any rogue or regional CSV files to enforce single accumulated files per category
    allowed_files = set(CATEGORY_FILE_MAP.values())
    for extra_file in MYMAPS_DIR.glob("*.csv"):
        if extra_file.name not in allowed_files:
            try:
                extra_file.unlink()
            except Exception:
                pass

    # Group by category
    grouped = {cat: [] for cat in CATEGORIES}
    for p in places:
        cat = p.get("category", "기타")
        if cat not in grouped:
            cat = "기타"
        grouped[cat].append(p)

    # Google My Maps optimal CSV fields:
    # 1. '장소 이름' -> Marker Title
    # 2. '검색위치' -> Marker Location/Geocoding query (combines clean name + region)
    # 3. '카테고리', '세부 태그/설명', '지역', '구글 지도 링크', '출처' -> Marker Info Card
    fieldnames = ["장소 이름", "검색위치", "카테고리", "세부 태그/설명", "지역", "구글 지도 링크", "출처"]
    
    for cat, items in grouped.items():
        filename = CATEGORY_FILE_MAP.get(cat, f"내지도_{cat}.csv")
        filepath = MYMAPS_DIR / filename
        
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


if __name__ == "__main__":
    places = load_places()
    print(f"Loaded {len(places)} places from storage.")
    sync_mymaps_csvs(places)
    print("MyMaps CSV sync complete.")
