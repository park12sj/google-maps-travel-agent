#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified CLI for Google Maps Places & Travel Planning Agent System.
"""

import sys
import argparse
import json
from pathlib import Path

from src.storage import (
    load_places,
    find_places_by_region_or_query,
    sync_mymaps_csvs,
    CATEGORIES,
    CATEGORY_FILE_MAP,
    MYMAPS_DIR
)
from src.place_extractor import process_url_and_save_places
from src.itinerary_generator import generate_itinerary
from src.profile_manager import load_profile, update_profile_with_feedback, PROFILE_MD_PATH


def handle_add_link(args):
    print(f"🔍 링크 분석 중: {args.url}")
    results = process_url_and_save_places(args.url, region_hint=args.region or "")
    if not results:
        print("⚠️ 장소를 자동으로 추출하지 못했습니다. 링크의 텍스트가 보호되어 있거나 장소명이 명시적이지 않을 수 있습니다.")
        print("💡 팁: AI Agent 대화창에서 링크를 공유해주시면 상세 본문을 읽어 직접 장소를 완벽하게 등록해드립니다.")
        return

    print(f"✨ 총 {len(results)}개의 장소를 수집하여 마스터 DB 및 MyMaps CSV에 누적 반영했습니다:")
    for item in results:
        p = item["place"]
        act = "신규 저장" if item["action"] == "added" else "기존 정보 업데이트"
        print(f" - [{p['category']}] {p['name']} ({act}) -> {p['google_maps_url']}")
    print("\n📁 지역별 MyMaps 폴더('data/mymaps/<지역>/') 및 통합 CSV에 모든 장소가 동기화되었습니다.")


def handle_mymaps(args):
    places = load_places()
    summary = sync_mymaps_csvs(places)
    print("=" * 65)
    print(f"🗺️ 구글 내 지도(My Maps) 지역별 & 카테고리별 CSV 현황 (총 {len(places)}곳)")
    print("=" * 65)
    
    print("\n📍 [지역별 내 지도 CSV 파일 현황]")
    for reg_name, info in sorted(summary["regions"].items(), key=lambda x: -x[1]["count"]):
        cat_str = ", ".join(f"{cat}: {cnt}곳" for cat, cnt in info["categories"].items())
        print(f" • 📁 {reg_name} (총 {info['count']}곳)")
        print(f"   - 경로: data/mymaps/{reg_name}/")
        print(f"   - 세부 분포: {cat_str}")
        print(f"   - 레이어 파일: 내지도_*.csv 및 {reg_name}_전체.csv")
        
    print("\n🌐 [전체 통합 CSV]")
    print(f" • 📁 _전체_통합 (총 {len(places)}곳)")
    print(f"   - 경로: data/mymaps/_전체_통합/ 및 data/mymaps/")
    
    print("\n💡 [구글 내 지도(mymaps.google.com) 활용 꿀팁]")
    print(" 1. 특정 여행지(예: 후쿠오카, 스페인 등)를 계획할 때:")
    print("    - 해당 지역 폴더(data/mymaps/<지역>/)의 '내지도_*.csv'를 레이어별로 업로드하세요.")
    print("    - 다른 나라 장소가 섞이지 않고 해당 여행지만 깔끔하게 지도에 핀으로 표시됩니다.")
    print(" 2. 레이어를 1개만 쓰고 싶다면:")
    print("    - '<지역>_전체.csv' 파일을 단일 레이어에 업로드하면 해당 지역 모든 장소가 한 번에 등록됩니다.")


def handle_plan(args):
    print(f"✈️ 여행 일정 생성 중... [숙소: {args.hotel}, 기간: {args.days}일]")
    result = generate_itinerary(
        hotel_info=args.hotel,
        days=args.days,
        region=args.region or "",
        additional_notes=args.notes or ""
    )
    print(f"✅ 여행 일정이 생성되었습니다!\n")
    print(f"📄 저장 위치: {result['file_path']}")
    print("\n" + "="*50 + "\n")
    print(result["markdown"])


def handle_feedback(args):
    feedback_text = args.text
    print(f"🧠 사용자 피드백 분석 중: \"{feedback_text}\"")
    result = update_profile_with_feedback(feedback_text)
    print("\n🎉 여행 스타일 프로필이 성공적으로 재구성되었습니다!")
    print(f" - 변경 시각: {result['timestamp']}")
    print(f" - 현재 여행 템포: {result['current_pace']} (하루 최대 {result['max_places_per_day']}곳)")
    print(f" - 하루 시작 시간: {result['morning_start_time']}")
    print("\n📌 적용된 상세 변경 내역:")
    for chg in result["changes"]:
        print(f"  ✓ {chg}")
    print(f"\n📄 최신 프로필 요약 파일: {PROFILE_MD_PATH}")


def handle_profile(args):
    if PROFILE_MD_PATH.exists():
        with open(PROFILE_MD_PATH, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        profile = load_profile()
        print(json.dumps(profile, ensure_ascii=False, indent=2))


def handle_list(args):
    places = find_places_by_region_or_query(args.query or "")
    if args.category:
        places = [p for p in places if p.get("category") == args.category]

    print(f"📍 저장된 장소 목록 (총 {len(places)}개):")
    for p in places:
        print(f" - [{p.get('category')}] {p.get('name')} | 지역: {p.get('region')} | {p.get('google_maps_url')}")


def handle_push(args):
    print("🚀 원격 저장소(origin main)로 최신 변경사항을 푸시합니다...")
    from src.git_sync import git_auto_push
    result = git_auto_push(commit_message=args.message)
    if result.get("success"):
        print(result.get("message"))
    else:
        print(f"❌ 푸시 실패: {result.get('reason')}")


def main():
    parser = argparse.ArgumentParser(description="구글 지도 저장함 및 여행 일정 지능형 에이전트 CLI")
    subparsers = parser.add_subparsers(dest="command", help="실행할 하위 명령")

    # add-link
    parser_add = subparsers.add_parser("add-link", help="유튜브/블로그/인스타그램 링크 속 장소 추출 및 저장")
    parser_add.add_argument("url", help="유튜브, 블로그 또는 인스타그램 URL")
    parser_add.add_argument("--region", "-r", help="지역/도시 힌트 (예: 도쿄, 바르셀로나)")

    # plan
    parser_plan = subparsers.add_parser("plan", help="숙소 및 여행 일수 기반 맞춤 일정 계획 생성")
    parser_plan.add_argument("--hotel", "-H", required=True, help="숙소 명칭 또는 주소/링크")
    parser_plan.add_argument("--days", "-d", type=int, default=3, help="여행 일수 (기본값: 3)")
    parser_plan.add_argument("--region", "-r", help="여행 지역/도시")
    parser_plan.add_argument("--notes", "-n", help="추가 요청사항")

    # feedback
    parser_fb = subparsers.add_parser("feedback", help="피드백 입력 및 여행 취향 프로필 자동 재구성")
    parser_fb.add_argument("text", help="계획에 대한 피드백 내용")

    # profile
    parser_prof = subparsers.add_parser("profile", help="현재 여행 취향 프로필 확인")

    # mymaps
    parser_mymaps = subparsers.add_parser("mymaps", help="구글 내 지도(My Maps) 카테고리별 누적 CSV 상태 확인 및 재생성")

    # list
    parser_list = subparsers.add_parser("list", help="저장된 장소 조회")
    parser_list.add_argument("--category", "-c", choices=CATEGORIES, help="카테고리 필터")
    parser_list.add_argument("--query", "-q", help="검색어")

    # push
    parser_push = subparsers.add_parser("push", help="원격 저장소(origin main)로 최신 변경사항 수동/강제 푸시")
    parser_push.add_argument("--message", "-m", help="커밋 메시지 (미지정 시 자동 생성)")

    args = parser.parse_args()

    if args.command == "add-link":
        handle_add_link(args)
    elif args.command == "mymaps":
        handle_mymaps(args)
    elif args.command == "plan":
        handle_plan(args)
    elif args.command == "feedback":
        handle_feedback(args)
    elif args.command == "profile":
        handle_profile(args)
    elif args.command == "list":
        handle_list(args)
    elif args.command == "push":
        handle_push(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
