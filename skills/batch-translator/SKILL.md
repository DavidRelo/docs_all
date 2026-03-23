---
name: batch-translator
description: "This skill should be used when the user asks to 'batch translate', '批量翻译', 'translate all files', 'translate multiple files', 'translate remaining files', 'continue translation', '继续翻译', or when there's a pending translation list file that needs processing. This skill handles large-scale translation tasks with progress tracking and resumption support."
---

# Batch Translator - 批量翻译

批量翻译 ZEGO 文档，支持进度跟踪和断点续传。

## 工作方式

使用 `sessions_spawn` 派生子 agent 执行实际翻译，避免阻塞主会话。子 agent 继承工作目录。

## 执行流程

### 1. 准备翻译工作区

如果是新任务，按 AGENTS.md 中的工作流创建翻译工作区：

```bash
cp -r ~/code/docs_all ~/code/translation/docs_all_translate_<task_name>
cd ~/code/translation/docs_all_translate_<task_name>
```

### 2. 检查已有待翻译列表

```bash
ls -t /tmp/docs-pending-translation-*.json /tmp/docs-git-changes-*.json 2>/dev/null | head -5
```

- 有文件 → 直接使用
- 有多个 → 用最新的或让用户选
- 没有 → 进入第 3 步收集文件

### 3. 收集待翻译文件

**方式 A: Git 变更**
```bash
python3 .claude/skills/collect-git-changes-for-translation/scripts/analyze_translation_changes.py . -o /tmp/docs-git-changes-$(date +%Y%m%d%H%M%S).json
```

**方式 B: 目录扫描**
```bash
python3 .claude/skills/collect-pending-translation-files/scripts/scan_pending_translation.py <directory> -o /tmp/docs-pending-translation-$(date +%Y%m%d%H%M%S).json
```

常用目录映射：
- AIAgent: `core_products/aiagent/zh` 或 `core_products/aiagent/en`
- Real-time Voice/Video: `core_products/real-time-voice-video/zh`
- ZIM: `core_products/zim/zh`
- Call Kit: `uikit_kits/call-kit/zh`

### 4. 读取文件列表

```bash
cat <pending_file> | jq -r '.files[]' 2>/dev/null || cat <pending_file> | jq -r '.details[].path' 2>/dev/null
```

### 5. 逐文件翻译

对每个文件，按 `translate-zh-to-en` skill 规则翻译：

1. **检查文件大小并读取源文件（重要）**:
   - 先统计行数：`wc -l <file_path>`
   - **> 500 行**：用 read 工具的 `offset` 和 `limit` 参数分段读取（如每段 300 行），避免上下文溢出
   - **≤ 500 行**：一次性读取整个文件
2. **跳过自动生成文件**（frontmatter 含 `api` 字段）
3. **加载术语表**（common + 产品专用）
4. **手动翻译**（非 API/自动翻译）
5. **验证**：grep 中文残留、检查 MDX 闭合标签
6. **更新进度**：从 pending list 中移除已完成文件

```bash
# 移除已完成条目（files 格式）
jq 'del(.files[] | select(. == "completed_file.mdx")) | .total_files = (.files | length)' <file> > <file>.tmp && mv <file>.tmp <file>

# 移除已完成条目（details 格式）
jq 'del(.details[] | select(.path == "completed_file.mdx")) | .total_files = (.details | length)' <file> > <file>.tmp && mv <file>.tmp <file>
```

### 6. YAML 文件翻译后重新生成 MDX

翻译完 openapi yaml 后需重新生成 mdx：

```bash
docuo god <openapi-group-name>
```

确认 yaml 已配置在 `docuo.config.json` 的 openapi 部分。

### 7. 进度报告

每翻译完一个文件报告：
```
✅ Translated: path/to/file.mdx
📊 Progress: X/Y files completed
```

## 质量规则

遵循 `translate-zh-to-en` skill 的所有规则，核心要点：

- **禁止使用自动翻译工具/API**
- **跳过 frontmatter 含 `api` 字段的文件**
- **保留 MDX/JSX 语法和闭合标签**
- **加载并应用术语表**
- **输出不得含中文或中文标点**
- **忠实翻译，不扩展不修饰**

## 异常处理

| 情况 | 处理 |
|------|------|
| pending list 为空 | 报告完成 |
| 文件不存在 | 跳过，从列表移除 |
| 自动生成文件 | 跳过，从列表移除 |
| 翻译失败 | 记录错误，保留在列表，继续下一个 |
| 中文残留 | 重翻该文件，不标记完成 |
| MDX 标签损坏 | 修复后再标记完成 |

## 断点续传

pending list 文件即进度记录。每次翻译完一个文件立即原子更新（写临时文件再 rename）。中断后下次运行读取更新后的列表继续。
