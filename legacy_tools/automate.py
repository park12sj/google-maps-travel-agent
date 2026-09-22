#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import json
import base64

def execute_js(js_code: str) -> str:
    # Wrap in IIFE and encode base64
    wrapped = f'''(() => {{
        try {{
            {js_code}
        }} catch(e) {{
            return "ERROR: " + e.message;
        }}
    }})()'''
    b64 = base64.b64encode(wrapped.encode('utf-8')).decode('ascii')
    applescript = f'''
    tell application "Whale"
        tell active tab of front window
            execute javascript "eval(decodeURIComponent(escape(window.atob('{b64}'))))"
        end tell
    end tell
    '''
    res = subprocess.run(['osascript'], input=applescript, text=True, capture_output=True)
    if res.returncode != 0:
        return f"APPLESCRIPT_ERROR: {res.stderr.strip()}"
    return res.stdout.strip()

if __name__ == "__main__":
    res = execute_js("return document.title;")
    print("Title:", res)
