#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Maps Takeout Saved Places Categorizer & Reorganizer
구글 테이크아웃(Takeout)으로 다운로드한 저장된 장소 데이터를
식당/카페, 숙박, 유적지/관광지, 쇼핑 등의 카테고리별로 자동 분류 및 재생성하는 도구
"""

import os
import sys
import csv
import json
import zipfile
import re
from pathlib import Path

# 카테고리 분류 규칙 (키워드 매칭)
CATEGORY_RULES = {
    "숙박": [
        "호텔", "호스텔", "게스트하우스", "리조트", "민박", "펜션", "모텔", "여관", "숙소", "비앤비",
        "hotel", "hostel", "resort", "lodging", "guest house", "inn", "bnb", "motel", "pousada", "albergue", "parador"
    ],
    "식당/카페": [
        "음식점", "식당", "맛집", "레스토랑", "카페", "커피", "베이커리", "빵", "제과", "바", "주점", "펍",
        "타파스", "비스트로", "와인", "피자", "파스타", "스테이크", "브런치", "디저트", "아이스크림", "젤라또",
        "해산물", "타코", "버거", "라멘", "초밥", "우동", "우육면", "딤섬", "찻집", "이자카야", "야시장",
        "restaurant", "cafe", "coffee", "bakery", "bar", "pub", "bistro", "wine", "tapas",
        "brunch", "dessert", "gelato", "pizza", "pasta", "food", "diner", "grill", "cerveceria", "churreria"
    ],
    "유적지/관광지": [
        "관광", "명소", "유적", "유적지", "성당", "교회", "사찰", "절", "신사", "모스크",
        "박물관", "미술관", "궁전", "성", "기념비", "전망대", "탑", "광장", "극장", "오페라", "문화재", "유네스코",
        "attraction", "sight", "landmark", "monument", "museum", "cathedral", "church", "basilica",
        "castle", "palace", "tower", "plaza", "square", "teatro", "miradouro", "viewpoint"
    ],
    "쇼핑/시장": [
        "시장", "마켓", "쇼핑", "쇼핑몰", "백화점", "마트", "슈퍼", "기념품", "상점", "아울렛",
        "market", "mercat", "mercado", "shopping", "mall", "store", "supermarket", "souvenir", "outlet"
    ],
    "자연/공원": [
        "공원", "정원", "해변", "비치", "호수", "산", "계곡", "국립공원", "자연", "산책로",
        "park", "garden", "beach", "playa", "lake", "mountain", "nature", "praia", "jardim", "parque"
    ]
}

def classify_place(title: str, note: str = "", address: str = "", category_hint: str = "") -> str:
    combined = f"{title} {note} {address} {category_hint}".lower()
    
    # 순서대로 검사 (숙박 -> 식당/카페 -> 유적지/관광지 -> 쇼핑 -> 자연)
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw.lower() in combined:
                return category
                
    return "기타 명소"

def parse_csv_file(file_path: Path):
    places = []
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']
    
    content = None
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
                break
        except UnicodeDecodeError:
            continue
            
    if content is None:
        print(f"⚠️ 인코딩을 읽을 수 없습니다: {file_path}")
        return places

    lines = content.splitlines()
    reader = csv.DictReader(lines)
    
    for row in reader:
        # 다양한 CSV 헤더 형식 지원 (Title / 이름, Note / 메모, URL / URL 등)
        title = row.get("Title") or row.get("이름") or row.get("Name") or ""
        note = row.get("Note") or row.get("메모") or row.get("Comment") or ""
        url = row.get("URL") or row.get("지도 URL") or row.get("Link") or ""
        address = row.get("Address") or row.get("주소") or ""
        
        if not title and not url:
            continue
            
        places.append({
            "source_list": file_path.stem,
            "title": title.strip(),
            "note": note.strip(),
            "url": url.strip(),
            "address": address.strip()
        })
        
    return places

def parse_geojson_file(file_path: Path):
    places = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        features = data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", []) if geom else []
            
            title = props.get("Title") or props.get("name") or props.get("이름") or ""
            note = props.get("Comment") or props.get("Note") or props.get("description") or ""
            url = props.get("google_maps_url") or props.get("url") or ""
            address = props.get("address") or ""
            
            places.append({
                "source_list": file_path.stem,
                "title": title.strip(),
                "note": note.strip(),
                "url": url.strip(),
                "address": address.strip(),
                "coordinates": coords
            })
    except Exception as e:
        print(f"⚠️ GeoJSON 파싱 오류 ({file_path}): {e}")
        
    return places

def extract_takeout_zip(zip_path: Path, extract_dir: Path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    print(f"📦 압축 해제 완료: {extract_dir}")

def process_directory(input_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    all_places = []

    # CSV 및 GeoJSON 파일 탐색
    for file in input_dir.rglob("*"):
        if file.suffix.lower() == '.csv':
            places = parse_csv_file(file)
            all_places.extend(places)
        elif file.suffix.lower() in ['.json', '.geojson']:
            places = parse_geojson_file(file)
            all_places.extend(places)

    if not all_places:
        print(f"❌ {input_dir} 에서 저장된 장소 파일을 찾지 못했습니다.")
        return

    print(f"📍 총 {len(all_places)}개의 저장된 장소를 수집했습니다.\n")

    # 카테고리별 분류
    categorized = {}
    for place in all_places:
        cat = classify_place(place["title"], place["note"], place["address"], place["source_list"])
        place["category"] = cat
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(place)

    # 분류 결과 요약 출력
    print("=" * 50)
    print("📊 [장소 분류 결과 요약]")
    print("=" * 50)
    for cat, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  • {cat:12s} : {len(items):3d}개 장소")
    print("=" * 50)

    # 1. 카테고리별 CSV 파일 저장 (구글 내 지도 My Maps 호환)
    for cat, items in categorized.items():
        safe_name = cat.replace("/", "_")
        cat_file = output_dir / f"분류_{safe_name}.csv"
        with open(cat_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["장소명", "기존_여행목록", "메모", "주소", "구글지도_URL"])
            for p in items:
                writer.writerow([p["title"], p["source_list"], p["note"], p["address"], p["url"]])

    # 2. 전체 통합 분류 CSV 저장
    combined_file = output_dir / "전체_재분류_장소목록.csv"
    with open(combined_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["새_카테고리", "장소명", "기존_여행목록", "메모", "주소", "구글지도_URL"])
        for cat, items in sorted(categorized.items()):
            for p in items:
                writer.writerow([cat, p["title"], p["source_list"], p["note"], p["address"], p["url"]])

    # 3. JSON 형식 저장
    json_file = output_dir / "categorized_places.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(categorized, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 분류 파일들이 '{output_dir}' 폴더에 성공적으로 생성되었습니다!")
    print(f"   1) 구글 내 지도(My Maps) 레이어별 import용 CSV 파일들: 분류_*.csv")
    print(f"   2) 전체 통합 확인용 파일: 전체_재분류_장소목록.csv\n")

if __name__ == "__main__":
    current_dir = Path(__file__).parent.resolve()
    input_dir = current_dir / "takeout_data"
    output_dir = current_dir / "reorganized_output"

    # 만약 명령행 인수로 zip이나 폴더가 전달된 경우
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1]).resolve()
        if arg_path.is_file() and arg_path.suffix.lower() == '.zip':
            extract_takeout_zip(arg_path, input_dir)
        elif arg_path.is_dir():
            input_dir = arg_path

    if not input_dir.exists():
        print(f"""
ℹ️ 사용 안내:
1. https://takeout.google.com 에 접속합니다.
2. 모두 선택 해제 후 [저장됨(Saved)] 또는 [지도(내 장소)]만 선택하여 내보내기를 생성/다운로드합니다.
3. 다운로드받은 zip 파일이나 압축 푼 폴더를 본 프로젝트 디렉토리({current_dir})에 놓아주세요.
4. 실행: python3 takeout_organizer.py [zip파일경로 또는 폴더]
""")
    else:
        process_directory(input_dir, output_dir)
