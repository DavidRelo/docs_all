#!/usr/bin/env python3
"""
Query PR records from /tmp/pr-records.json.
Optionally update PR status from GitHub and cleanup old closed records.

Usage:
    # Query all PRs (cleanup enabled by default)
    python3 query_pr.py

    # Query by agent ID
    python3 query_pr.py --agent-id writer

    # Filter by status
    python3 query_pr.py --status open

    # Skip cleanup
    python3 query_pr.py --no-cleanup

    # Skip status update from GitHub
    python3 query_pr.py --no-update-status
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PR_RECORDS_FILE = "/tmp/pr-records.json"

# Closed PRs older than this are removed during cleanup
CLEANUP_THRESHOLD_DAYS = 7


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


def fetch_pr_status(pr_number: int, repo: str) -> str | None:
    """Query PR status from GitHub via gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--repo", repo,
             "--json", "state", "--jq", ".state"],
            capture_output=True, text=True, check=True,
        )
        state = result.stdout.strip().lower()
        # GitHub states: open, closed, merged
        return state
    except subprocess.CalledProcessError:
        return None


def parse_time(time_str: str) -> datetime:
    """Parse ISO format datetime string."""
    # Handle both with and without timezone info
    if time_str.endswith("Z"):
        time_str = time_str[:-1] + "+00:00"
    return datetime.fromisoformat(time_str)


def main():
    parser = argparse.ArgumentParser(description="Query PR records")
    parser.add_argument("--agent-id", default=None,
                        help="Filter by agent ID (returns all if not specified)")
    parser.add_argument("--status", default=None,
                        choices=["open", "closed", "merged", "all"],
                        help="Filter by status (default: all)")
    parser.add_argument("--repo", default="ZEGOCLOUD/docs_all",
                        help="Repository for GitHub queries")
    parser.add_argument("--no-update-status", action="store_true",
                        help="Skip updating PR status from GitHub")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Skip cleanup of old closed records")
    args = parser.parse_args()

    records = load_records()

    if not records:
        print(json.dumps({"success": True, "records": {}, "total": 0},
                         indent=2, ensure_ascii=False))
        return

    # Update status from GitHub
    if not args.no_update_status:
        updated_count = 0
        for key, record in records.items():
            pr_number = record.get("pr_number")
            if not pr_number:
                continue
            current_status = record.get("status", "open")
            # Only query GitHub for open PRs (closed/merged are final)
            if current_status == "open":
                gh_status = fetch_pr_status(pr_number, args.repo)
                if gh_status and gh_status != current_status:
                    record["status"] = gh_status
                    updated_count += 1
        if updated_count > 0:
            save_records(records)
            print(f"Updated {updated_count} PR status(es) from GitHub", file=sys.stderr)

    # Cleanup old closed records
    if not args.no_cleanup:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=CLEANUP_THRESHOLD_DAYS)
        to_remove = []
        for key, record in records.items():
            status = record.get("status", "open")
            if status in ("closed", "merged"):
                try:
                    record_time = parse_time(record.get("time", ""))
                    if record_time < threshold:
                        to_remove.append(key)
                except (ValueError, TypeError):
                    pass
        if to_remove:
            for key in to_remove:
                del records[key]
            save_records(records)
            print(f"Cleaned up {len(to_remove)} old closed/merged record(s)", file=sys.stderr)

    # Filter results
    filtered = {}
    for key, record in records.items():
        # Filter by agent-id
        if args.agent_id and record.get("agent_id") != args.agent_id:
            continue
        # Filter by status
        if args.status and args.status != "all" and record.get("status") != args.status:
            continue
        filtered[key] = record

    result = {
        "success": True,
        "total": len(filtered),
        "records": filtered,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
