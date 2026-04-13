---
name: manage-docs-workspace
description: "This skill should be used when the user asks to 'create workspace', '新建工作区', 'delete workspace', '删除工作区', 'start docs task', '开始文档任务', 'prepare workspace', '准备工作区', 'sync upstream', '同步上游'. 基于 git worktree 为文档任务创建或删除隔离工作区，自动同步 upstream 并管理 fork 远端。"
---

# 文档工作区管理

基于 git worktree 为文档任务创建/删除隔离工作区。主仓库 `~/code/docs_all`，工作区目录统一在 `~/code/` 下。

## 创建工作区

```bash
# 基于最新 main 创建
python3 ~/.openclaw/skills/manage-docs-workspace/scripts/workspace-manager.py create --agent <agentname> --job <jobname>

# 基于上游指定分支创建（用户指定了上游分支时使用）
python3 ~/.openclaw/skills/manage-docs-workspace/scripts/workspace-manager.py create --agent <agentname> --job <jobname> --branch <upstream_branch>
```

脚本执行流程：
1. 校验 `--job` 格式（仅 `[a-zA-Z0-9_]+`），不符合则报错退出
2. 检查工作区目录和分支是否已存在
3. `git fetch upstream` 拉取上游最新代码
4. `gh repo sync` 同步 fork 远端 origin（main + 指定分支）
5. 如指定 `--branch`：验证该分支在 upstream 存在，不存在则报错退出
6. 基于 `upstream/main`（或 `upstream/<branch>`）创建 worktree

输出 JSON：
```json
{"status": "created", "worktree_dir": "/home/doc/code/docs_all_<agent>_<job>", "branch": "<job>"}
```

创建后 **cd 到 `worktree_dir` 开始工作**。

## 删除工作区

```bash
python3 ~/.openclaw/skills/manage-docs-workspace/scripts/workspace-manager.py delete --agent <agentname> --job <jobname>
```

强制移除 worktree 目录和对应分支。输出同格式的 JSON，`status` 为 `"deleted"`。

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--agent` | 是 | agent 名称（如 `writer`, `translator`） |
| `--job` | 是 | 任务名称，仅允许英文字母、数字和下划线 |
| `--branch` | 否 | 上游基准分支名（如 `custom-video`），不指定则基于 main |

## 命名规则

- 工作区目录：`~/code/docs_all_{agentname}_{jobname}`
- 分支名：`{jobname}`
- 主仓库：`~/code/docs_all`

## 注意事项

- 创建不影响主仓库的工作区状态（不 checkout、不 pull 主仓库）
- fork 仓库会自动用 `gh repo sync` 同步远端 origin
- 删除操作会强制移除 worktree 和对应分支，不可恢复

## 脚本源码

详细逻辑见 `scripts/workspace-manager.py`，需要调试或修补时直接读取该文件。
