---
name: feishu-send-file
description: "Send files to users via Feishu (Lark). Use when the user asks to send a file, document, image, PDF, or any attachment through Feishu. 触发短语: 'send file', '发文件', '发送文件', 'send attachment', '发个文件', '发图片'."
---

# Send Files via Feishu

## Requirements

1. Feishu app must have these permissions:
   - `im:resource` — upload media resources
   - `im:message:send_as_bot` — send messages as bot
2. File must be under the **workspace directory** (`~/.openclaw/workspace/` or the configured workspace). Files outside workspace (e.g. `/tmp/`) will be rejected with `path-not-allowed` error.

## Usage

Use the `message` tool:

```
message(action=send, channel=feishu, filePath="/path/to/file", caption="optional description")
```

### Parameters

- `filePath`: Absolute path to the file (must be under workspace)
- `caption`: Optional text description
- `filename`: Optional filename override
- `media`: URL of a remote file (alternative to filePath)
- `buffer`: Base64-encoded file content (alternative to filePath)

### Steps

1. If file is not in workspace, copy it there first: `cp /source/file ~/.openclaw/workspace/media-send-to-user`
2. Send via `message` tool with `filePath`
3. Verify the result — if only text is received (no file), check logs: `openclaw logs 2>&1 | grep -i "feishu.*error\|path-not-allowed"`
4. **Clean up**: After sending, delete the temporary file from workspace: `rm ~/.openclaw/workspace/media-send-to-user/<filename>`. If the directory is empty, remove it too.

### Supported types

Images, PDF, documents, audio, video — max 30MB per file.

### Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `path-not-allowed` | File outside workspace | Copy file to workspace first |
| `99991672` | Missing `im:resource` or `im:message:send_as_bot` | Add permission in Feishu Open Platform |
| Only text received | File upload failed | Check logs for error details |
