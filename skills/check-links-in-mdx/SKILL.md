---
name: check-links-in-mdx
description: "This skill checks whether links in MDX documentation files are valid. Use when the user wants to validate links in a single MDX file or all files under a documentation instance. Also manages batch link checking across all instances with status tracking. 触发短语: 'check links', '检查链接', 'validate links', '验证链接', 'find broken links', '查找断链', 'check for link errors', '检查链接错误', 'run link checker', '运行链接检查', '断链检查'."
---

# check-links-in-mdx

Check whether links in MDX documentation files are valid by running the link checker script. Includes a link check manager for tracking which instances have been checked.

## Instance Check Management

The link check manager tracks which instances have been checked and their fix status. Records are stored in `~/.zego-docs-fix-links-record.json` and should only be modified through the manager script.

### Manager Script Location

```
scripts/link_check_manager.py
```

### Status Values

- `init`: Never checked (initial state)
- `editing`: Currently being fixed
- `failed`: Fix attempt failed, needs retry
- `done`: All links verified/fixed

### Initialize Records

First time use or reset all records:

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --init
```
Output: `{"zh": N, "en": M, "total": N+M}`

### Count Unchecked Instances

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --count
```
Output: `{"zh": 42, "en": 28}`

### Get Unchecked Instances

Returns unchecked instance IDs for the specified language (defaults to `--zh`):

```bash
# Get 1 Chinese unchecked instance (default)
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --get

# Get 5 English unchecked instances
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --en --get 5
```
Output: `{"language": "zh", "instances": ["id1", "id2"], "count": 2}`

### Update Instance Status

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --update <instance_id> <status>
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --en --update <instance_id> <status>
```
Output: `{"language": "zh", "instance_id": "...", "status": "done", "last_fix_time": "2026-04-13"}`

## Batch Processing Workflow

For systematically checking all instances:

1. Initialize tracking (first time only):
```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --init
```

2. Check progress:
```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --count
```

3. Get an unchecked instance:
```bash
INSTANCE=$(python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --get | jq -r '.instances[0]')
```

4. Update status to `editing` before starting:
```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --update "$INSTANCE" editing
```

5. Check links in the instance (see below for details)

6. After fixing, update status to `done`:
```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --update "$INSTANCE" done
```

## How to use

This skill runs the link checker script non-interactively to validate links in MDX files.

### Remove old link check results

```bash
rm -rf /tmp/check_link_result.json
```

### Check all links in an instance

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --instance "<instance-id>"
```
You can pass the instance path to the script instead of the instance ID.

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --instance-path "<path-to-instance>"
```

### Check links in a specific file

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --file "<path-to-file.mdx>"
```

### Check links with remote URL validation

```bash
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --instance "<instance-id>" --remote
```

**Arguments:**
- `--zh` / `--en`: Language option (`--zh` for Chinese, `--en` for English)
- `--instance`: Instance ID to check (use exact instance name from docuo config)
- `--instance-path`: Path to instance directory
- `--file`: Specific MDX file path to check (relative to repo root or absolute)
- `--remote`: Also check remote external links (slower, requires network)

**Output:**
- Console output with categorized link issues
- Results saved to `/tmp/check_link_result.json`

## Example

```bash
# Check all links in the macOS Objective-C real-time video instance
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --instance real_time_video_ios_oc_zh

# Check a specific file
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --file "core_products/real-time-voice-video/zh/macos-oc/client-sdk/api-reference/function-list.mdx"

# Check with remote URL validation
python3 ~/.openclaw/skills/check-links-in-mdx/scripts/check_links.py --zh --instance real_time_video_ios_oc_zh --remote
```

## How it works (internal)

1. Read docuo config file (zh/en) based on language argument
2. Load instances from config and validate the provided instance ID
3. Scan MDX files and extract all links (anchor, internal, external, relative)
4. Validate each link type:
   - **Anchor links**: Check if target heading/ParamField anchor exists in target file
   - **Internal links**: Verify target MDX file exists with URL path
   - **Relative links**: Resolve path and verify file exists
   - **External links** (--remote only): HTTP request to verify accessibility
5. Categorize issues by type:
   - Invalid anchor links
   - Broken internal links
   - Language mixing (Chinese doc with zegocloud.com or English doc with zego.im)
   - Unreachable external links
6. Save results to `check_link_result.json` with categorized issues

## Getting instance IDs

To find available instance IDs:
- **Method 1**: Use the manager (recommended for batch processing)
  ```bash
  python3 ~/.openclaw/skills/check-links-in-mdx/scripts/link_check_manager.py --zh --get
  ```
- **Method 2**: Read config files directly
  - Chinese: `docuo.config.zh.json` → `instances` array
  - English: `docuo.config.en.json` → `instances` array

Each instance has an `id` field that can be passed to `--instance`.
