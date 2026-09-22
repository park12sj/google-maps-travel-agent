#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git Remote Sync Module.
Provides automatic git commit and remote push functions by default
whenever places, itineraries, or profiles are updated.
"""

import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent


def git_auto_push(commit_message=None, cwd=None):
    """
    Stage all modified/untracked files, create a commit, and push to origin main.
    Returns dict with status, returncode, and message.
    """
    target_dir = cwd or BASE_DIR
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not commit_message:
        commit_message = f"chore(auto-sync): 여행 에이전트 데이터 자동 동기화 ({now_str})"

    try:
        # 1. Check if git repo
        check_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        if check_repo.returncode != 0:
            return {"success": False, "reason": "Not a git repository"}

        # 2. Stage changes
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True)

        # 3. Check if there are staged changes
        staged_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=target_dir
        )
        if staged_check.returncode == 0:
            # No changes staged
            return {"success": True, "pushed": False, "message": "변경 사항이 없어 푸시를 건너뜁니다."}

        # 4. Commit
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        if commit_res.returncode != 0:
            return {"success": False, "reason": f"Commit failed: {commit_res.stderr.strip()}"}

        # 5. Push to origin main
        push_res = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        if push_res.returncode != 0:
            # Try plain git push if origin main fails
            fallback_push = subprocess.run(
                ["git", "push"],
                cwd=target_dir,
                capture_output=True,
                text=True
            )
            if fallback_push.returncode != 0:
                return {"success": False, "reason": f"Push failed: {push_res.stderr.strip()} | {fallback_push.stderr.strip()}"}

        return {
            "success": True,
            "pushed": True,
            "commit_message": commit_message,
            "message": f"🚀 원격 저장소(origin main)로 자동 푸시 완료: '{commit_message}'"
        }

    except Exception as e:
        return {"success": False, "reason": f"Exception during git push: {str(e)}"}


if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    res = git_auto_push(msg)
    print(res.get("message") or res.get("reason"))
