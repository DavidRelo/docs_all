# HEARTBEAT.md

## 翻译进度检查（每10分钟）

检查两个翻译子 agent 的进度，飞书报告给老板：

1. `aiagent-translate` — 20 文件，pending list: /tmp/aiagent-pending-20260320111530.json
2. `digital-human-translate` — 67 文件，pending list: /tmp/digital-human-pending-20260320112137.json

检查方法：
- 读取 pending list 文件，看剩余文件数 = total_files - 原始数量
- 如果文件不存在或为空，说明任务已完成或出错

报告格式：
```
📊 翻译进度报告
⏰ 时间: XX:XX

🟢 AIAgent: X/20 (XX%)
🟢 数字人: X/67 (XX%)
```

如果两个任务都完成了，发完报告后清空此文件停止检查。
