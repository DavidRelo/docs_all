---
name: manage-pr
description: "Manage GitHub PRs: create PRs with validation, query PR records, and track PR status. Use when creating a PR, querying PRs, checking PR status, or listing PRs by agent. Supports ASCII title validation and centralized PR tracking."
---

# Manage PR

Create and query GitHub Pull Requests with centralized tracking at `/tmp/pr-records.json`.

## When to Use

- Creating a new PR for documentation changes
- Querying existing PRs (all or by agent)
- Checking PR status updates
- When user asks "what PRs are open", "list my PRs", "check PR status"

## Prerequisites

Ensure `gh` CLI is installed and authenticated:

```bash
gh --version && gh auth status
```

## Create PR

Use `create_pr.py` to create a PR and record it.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--agent-id` | Yes | Your agent identifier (e.g., "writer", "translator", "main") |
| `--session-id` | Yes | OpenClaw current session identifier |
| `--working-dir` | Yes | Agent's working directory(worktree_dir) |
| `--products` | Yes | Product numbers (1-10), space-separated |
| `--desc` | Yes | Change description (must be ASCII) |
| `--issues` | No | Issue numbers, space-separated |
| `--repo` | No | Target repo (default: ZEGOCLOUD/docs_all) |
| `--base` | No | Base branch (default: main) |

> **Note:** The script automatically pushes the current branch to `origin` (fork) before creating the PR, and sets `--head` to `fork_owner:branch` for cross-fork PR creation.

### Product Numbers

| # | Product |
|---|---------|
| 1 | RTC (实时音视频/实时语音/超低延迟直播) |
| 2 | ZIM (即时通讯) |
| 3 | AIAgent (AI 智能体) |
| 4 | Digital Human (数字人) |
| 5 | UIKit (CallKit/LiveStreamingKit/LiveAudioRoomKit/VideoConferenceKit) |
| 6 | Extension Service (超级白板/云端播放器/云端录制等) |
| 7 | Solution |
| 8 | General (控制台/政策与协议/词汇表) |
| 9 | FAQ (常见问题) |
| 10 | 其他 |

### Example

```bash
python3 ~/.openclaw/skills/manage-pr/scripts/create_pr.py \
    --agent-id writer \
    --session-id "c46993dd-7647-45ba-a24e-f232b139ec4b" \
    --working-dir "/home/doc/code/writer/docs_all_v280" \
    --products 1 3 \
    --desc "Add new API docs for RTC and AIAgent" \
    --issues 1234 5678
```

### ASCII Validation

The script validates that the generated PR title is pure ASCII. If the description contains non-ASCII characters (e.g., Chinese), the script will **fail** with an error. Use English for the `--desc` parameter.

### Output

Returns JSON with:
- `pr_url`: GitHub PR URL
- `pr_number`: PR number
- `title`: Generated PR title
- `record`: Full record saved to tracking file

## Query PRs

Use `query_pr.py` to query and manage PR records.

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--agent-id` | No | Filter by agent ID (omit for all) |
| `--status` | No | Filter: open/closed/merged/all (default: all) |
| `--repo` | No | Repo for GitHub queries (default: ZEGOCLOUD/docs_all) |
| `--no-update-status` | No | Skip fetching latest status from GitHub |
| `--no-cleanup` | No | Skip removing old closed records |

### Default Behavior

- **Status update**: Enabled by default — queries GitHub for open PRs to check if they've been closed/merged
- **Cleanup**: Enabled by default — removes closed/merged PRs older than 7 days

### Examples

```bash
# Query all PRs (auto-update status + cleanup)
python3 ~/.openclaw/skills/manage-pr/scripts/query_pr.py

# Query PRs for a specific agent
python3 ~/.openclaw/skills/manage-pr/scripts/query_pr.py --agent-id writer

# Query only open PRs
python3 ~/.openclaw/skills/manage-pr/scripts/query_pr.py --status open

# Quick query without GitHub API calls
python3 ~/.openclaw/skills/manage-pr/scripts/query_pr.py --no-update-status
```

### Output

Returns JSON:
```json
{
  "success": true,
  "total": 2,
  "records": {
    "123": {
      "pr_number": 123,
      "agent_id": "writer",
      "session_id": "abc123",
      "status": "open",
      "time": "2026-04-10T08:30:00+00:00",
      "working_dir": "/home/doc/code/writer/docs_all_v280",
      "desc": "Add new API docs for RTC and AIAgent",
      "products": ["RTC", "AIAgent"]
    }
  }
}
```

## PR Record Format

Each record in `/tmp/pr-records.json`:

| Field | Description |
|-------|-------------|
| `pr_number` | GitHub PR number |
| `agent_id` | Which agent created the PR |
| `session_id` | Session that created the PR |
| `status` | Current status: open/closed/merged |
| `time` | Creation time (ISO 8601 UTC) |
| `working_dir` | Working directory when PR was created |
| `desc` | Change description |
| `products` | List of product names involved |

## Workflow

### Creating a PR

1. Ensure code is committed and pushed to the remote branch
2. Run `create_pr.py` with required parameters
3. If title fails ASCII validation, rewrite `--desc` in English
4. On success, share the `pr_url` with the user

### Querying PRs

1. Run `query_pr.py` with desired filters
2. The script auto-updates open PR statuses from GitHub
3. Old closed records (>7 days) are auto-cleaned
4. Report results to the user

## Error Handling

- **Non-ASCII title**: Rewrite description in English and retry
- **gh CLI not authenticated**: Inform user to run `gh auth login`
- **No changes to PR**: Branch may not be pushed — run `git push origin <branch>` first
- **PR already exists**: Use `query_pr.py` to find the existing record
