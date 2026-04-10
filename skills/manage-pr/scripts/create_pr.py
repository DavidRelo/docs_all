#!/usr/bin/env python3
"""
Create a GitHub PR and record it to /tmp/pr-records.json.

Usage:
    python3 create_pr.py \
        --agent-id writer \
        --session-id abc123 \
        --products 1 3 \
        --desc "Add new API docs for RTC and AIAgent" \
        --issues 1234 5678

The PR title must be pure ASCII. If not, the script exits with error.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PR_RECORDS_FILE = "/tmp/pr-records.json"

PRODUCT_MAP = {
    1: "RTC",
    2: "ZIM",
    3: "AIAgent",
    4: "Digital Human",
    5: "UIKit",
    6: "Extension Service",
    7: "Solution",
    8: "General",
    9: "FAQ",
    10: "Other",
}


def is_ascii(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def load_records() -> dict:
    p = Path(PR_RECORDS_FILE)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_records(records: dict):
    p = Path(PR_RECORDS_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def build_title(products: list[int], desc: str) -> str:
    names = [PRODUCT_MAP.get(n, f"Unknown({n})") for n in products]
    prefix = "/".join(names)
    return f"[{prefix}] {desc}"


def build_body(products: list[int], desc: str, issues: list[str]) -> str:
    # Build product checkboxes
    all_products = [
        (1, "RTC", "实时音视频/实时语音/超低延迟直播"),
        (2, "ZIM", "即时通讯"),
        (3, "AIAgent", "AI 智能体"),
        (4, "Digital Human", "数字人"),
        (5, "UIKit", "CallKit/LiveStreamingKit/LiveAudioRoomKit/VideoConferenceKit"),
        (6, "Extension Service", "超级白板/云端播放器/云端实时 ASR/云端录制/AI美颜/本地服务端录制/星图"),
        (7, "Solution", ""),
        (8, "General", "控制台/政策与协议/词汇表"),
        (9, "FAQ", "常见问题"),
        (10, "其他", ""),
    ]

    checkbox_lines = []
    for num, name, detail in all_products:
        checked = "x" if num in products else " "
        label = f"{name} ({detail})" if detail else name
        checkbox_lines.append(f"- [{checked}] {label}")

    product_section = "\n".join(checkbox_lines)

    # Build issue section
    issue_section = ""
    if issues:
        issue_refs = " ".join(f"#{i}" for i in issues)
        issue_section = issue_refs
    else:
        issue_section = "无"

    return f"""## 涉及产品

{product_section}

## 变更描述

{desc}

## 相关 Issue

{issue_section}
"""


def main():
    parser = argparse.ArgumentParser(description="Create a PR and record it")
    parser.add_argument("--agent-id", required=True, help="Agent identifier")
    parser.add_argument("--session-id", required=True, help="Session identifier")
    parser.add_argument("--products", nargs="+", type=int, required=True,
                        help="Product numbers (1-10), space-separated")
    parser.add_argument("--desc", required=True, help="Change description")
    parser.add_argument("--issues", nargs="+", default=[],
                        help="Issue numbers (space-separated, optional)")
    parser.add_argument("--repo", default="ZEGOCLOUD/docs_all",
                        help="Target repository (default: ZEGOCLOUD/docs_all)")
    parser.add_argument("--base", default="main",
                        help="Base branch (default: main)")
    args = parser.parse_args()

    # Validate product numbers
    for p in args.products:
        if p not in PRODUCT_MAP:
            print(f"Error: Invalid product number {p}. Must be 1-{len(PRODUCT_MAP)}", file=sys.stderr)
            sys.exit(1)

    # Build title and validate ASCII
    title = build_title(args.products, args.desc)
    if not is_ascii(title):
        non_ascii = [c for c in title if ord(c) >= 128]
        print(f"Error: PR title contains non-ASCII characters: {non_ascii}", file=sys.stderr)
        print(f"Title: {title}", file=sys.stderr)
        print("Please use only ASCII characters in the description.", file=sys.stderr)
        sys.exit(1)

    # Build PR body
    body = build_body(args.products, args.desc, args.issues)

    # Write body to temp file
    body_file = "/tmp/pr-body.md"
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(body)

    # Create PR via gh CLI
    cmd = [
        "gh", "pr", "create",
        "--title", title,
        "--body-file", body_file,
        "--repo", args.repo,
        "--base", args.base,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to create PR: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Cleanup temp file
        if os.path.exists(body_file):
            os.remove(body_file)

    # Extract PR number from URL
    # Output format: https://github.com/ZEGOCLOUD/docs_all/pull/123
    pr_number = None
    match = re.search(r"/pull/(\d+)", output)
    if match:
        pr_number = int(match.group(1))
    else:
        print(f"Warning: Could not parse PR number from output: {output}", file=sys.stderr)

    # Record PR
    records = load_records()
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "pr_number": pr_number,
        "agent_id": args.agent_id,
        "session_id": args.session_id,
        "status": "open",
        "time": now,
        "working_dir": os.getcwd(),
        "desc": args.desc,
        "products": [PRODUCT_MAP[p] for p in args.products],
    }

    key = str(pr_number) if pr_number else f"unknown-{now}"
    records[key] = record
    save_records(records)

    result = {
        "success": True,
        "pr_url": output,
        "pr_number": pr_number,
        "title": title,
        "record": record,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
