#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import time
import json
import ctypes
from ctypes import c_void_p, c_int, c_double, c_uint32, Structure
from automate import execute_js

# Load CoreGraphics
cg = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')

class CGPoint(Structure):
    _fields_ = [('x', c_double), ('y', c_double)]

cg.CGEventCreateMouseEvent.restype = c_void_p
cg.CGEventCreateMouseEvent.argtypes = [c_void_p, c_uint32, CGPoint, c_uint32]
cg.CGEventPost.restype = None
cg.CGEventPost.argtypes = [c_uint32, c_void_p]

kCGEventLeftMouseDown = 1
kCGEventLeftMouseUp = 2
kCGEventMouseMoved = 5
kCGHIDEventTap = 0

def real_click(x: float, y: float):
    pt = CGPoint(x, y)
    
    # 1. Move
    ev_move = cg.CGEventCreateMouseEvent(None, kCGEventMouseMoved, pt, 0)
    cg.CGEventPost(kCGHIDEventTap, ev_move)
    time.sleep(0.05)
    
    # 2. Down
    ev_down = cg.CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, pt, 0)
    cg.CGEventPost(kCGHIDEventTap, ev_down)
    time.sleep(0.08)
    
    # 3. Up
    ev_up = cg.CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, pt, 0)
    cg.CGEventPost(kCGHIDEventTap, ev_up)

def activate_whale():
    subprocess.run(['osascript', '-e', 'tell application "Whale" to activate'])

def get_element_coords(item_text: str):
    code = f'''
    const el = Array.from(document.querySelectorAll('*')).find(e => e.innerText === '{item_text}');
    if (!el) return null;
    const btn = el.closest('button, a, div[role="button"]') || el;
    const rect = btn.getBoundingClientRect();
    const topChrome = window.outerHeight - window.innerHeight;
    return JSON.stringify({{
        x: window.screenX + rect.left + rect.width / 2,
        y: window.screenY + topChrome + rect.top + rect.height / 2,
        text: el.innerText
    }});
    '''
    res = execute_js(code)
    try:
        return json.loads(res)
    except:
        return None

if __name__ == "__main__":
    coords = get_element_coords("2026 대만")
    print("Found coords for 2026 대만:", coords)
    if coords:
        activate_whale()
        time.sleep(0.2)
        print(f"Clicking at ({coords['x']}, {coords['y']})...")
        real_click(coords['x'], coords['y'])
        time.sleep(1.5)
        
        # Check text
        check = execute_js("return document.body.innerText.slice(0, 400);")
        print("Page text snippet:", repr(check[:200]))
