---
name: fix-chinese-english-links-mixed
description: "This skill fixes Chinese-English domain mixing errors in MDX documentation where links point to the wrong language domain. Use when Chinese documents contain zegocloud.com URLs (should be zego.im) or English documents contain zego.im URLs (should be zegocloud.com). 触发短语: 'fix mixed links', '修复中英文链接混用', 'wrong domain', '域名错误', 'convert zego.im to zegocloud', 'convert zegocloud to zego.im', '语言域名错误', 'fix language domain'."
---

# fix-chinese-english-links-mixed

Fix Chinese-English domain mixing errors.

## Domain Conversion Rules

| Document Language | Wrong Domain | Correct Domain |
|-------------------|--------------|----------------|
| Chinese (zh) | `zegocloud.com` / `www.zegocloud.com` | `doc-zh.zego.im` |
| English (en) | `zego.im` / `doc-zh.zego.im` | `zegocloud.com` / `www.zegocloud.com` |

**Note**: `doc-zh.zego.im` is the Chinese docs subdomain; `www.zegocloud.com/docs` is the English docs path.

## Shared Domains (Skip These)

Do NOT modify links containing these domains:
- `artifact-sdk.zego.im`
- `artifact-demo.zego.im`
- `doc-media.zego.im`
- `site-media.zego.im`
- `storage.zego.im`
- `www.zego.im` with demo or artifact paths(e.g., `https://www.zego.im/audio-demo`)

## How to Fix

1. **Detect document language** from file path (contains `/zh/` or `/en/`) or user input
2. **Replace domain** based on the rules above
3. **Verify the change** by checking the link format is correct

## Example

**Chinese doc** (`/zh/android/quick-start.mdx`):
```
# Before
[Link](https://www.zegocloud.com/docs/aiagent-android/quick-start)

# After
[Link](https://doc-zh.zego.im/aiagent-android/quick-start)
```

**English doc** (`/en/android/quick-start.mdx`):
```
# Before
[Link](https://doc-zh.zego.im/aiagent-android/quick-start)

# After
[Link](https://www.zegocloud.com/docs/aiagent-android/quick-start)
```

## 特例

`https://doc-zh.zego.im/article/api?doc=xxx` 这种形式的链接，在英文应该对应的是`https://www.zegocloud.com/article/api?doc=`,不必加/docs，因为这种形式的API都在老系统。