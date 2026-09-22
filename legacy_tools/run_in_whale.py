#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whale 브라우저의 구글 지도 탭에서 자동화 스크립트를 원격 실행하는 도구
"""

import subprocess
import sys
import json
from pathlib import Path

def run_applescript(scpt: str) -> tuple[int, str]:
    proc = subprocess.run(['osascript', '-e', scpt], capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()

def check_whale_tab():
    scpt = 'tell application "Whale" to get URL of active tab of front window'
    code, out = run_applescript(scpt)
    if code != 0:
        print("❌ Whale 브라우저가 실행 중이지 않거나 창을 찾을 수 없습니다.")
        return None
    return out

def check_applescript_js_enabled():
    scpt = 'tell application "Whale" to tell active tab of front window to execute javascript "1 + 1"'
    code, out = run_applescript(scpt)
    if code == 0:
        return True, out
    return False, out

def execute_js_in_whale(js_code: str):
    # JavaScript 코드를 안전하게 JSON 문자열로 인코딩하여 AppleScript에 삽입
    encoded_js = json.dumps(js_code)
    scpt = f'''
    tell application "Whale"
        tell active tab of front window
            execute javascript {encoded_js}
        end tell
    end tell
    '''
    return run_applescript(scpt)

def main():
    print("🔍 Whale 브라우저 상태를 확인합니다...")
    url = check_whale_tab()
    if not url:
        sys.exit(1)
        
    print(f"📍 현재 활성화된 탭 URL: {url}")
    if "google" not in url or "maps" not in url:
        print("⚠️ 현재 활성 탭이 구글 지도가 아닙니다. 구글 지도 탭을 열어주세요.")
        sys.exit(1)

    print("🔐 자바스크립트 원격 제어 권한 확인 중...")
    enabled, msg = check_applescript_js_enabled()
    if not enabled:
        print("\n" + "=" * 60)
        print("🚨 [권한 설정 필요] Whale 브라우저 보안 설정이 꺼져 있습니다.")
        print("Whale 메뉴 바에서 아래 항목을 '단 1번만' 클릭해 체크해주세요:")
        print("👉 Whale 상단 메뉴 바: [보기] -> [개발자] -> [Apple Events의 자바스크립트 허용]")
        print("=" * 60 + "\n")
        sys.exit(2)

    print("✅ 권한 확인 완료! 구글 지도 정리 스크립트를 Whale에서 실행합니다...")
    script_path = Path(__file__).parent / "google_maps_console_organizer.js"
    js_code = script_path.read_text(encoding="utf-8")
    
    code, result = execute_js_in_whale(js_code)
    if code == 0:
        print("🎉 스크립트가 성공적으로 전달되어 Whale에서 실행 중입니다!")
        print(f"결과: {result}")
    else:
        print(f"❌ 실행 실패: {result}")

if __name__ == "__main__":
    main()
