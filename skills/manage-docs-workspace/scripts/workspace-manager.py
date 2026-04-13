#!/usr/bin/env python3
"""文档工作区管理工具 - 基于 git worktree 管理文档任务工作区。

用法:
  python workspace-manager.py create --agent <name> --job <name>
  python workspace-manager.py delete --agent <name> --job <name>
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MAIN_REPO = Path.home() / "code" / "docs_all"


def run_git(*args, cwd=None, check=True):
    """执行 git 命令并返回结果。"""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd or MAIN_REPO,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"错误: git {' '.join(args)} 失败", file=sys.stderr)
        if result.stderr.strip():
            print(f"  {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result


def validate_params(agent, job):
    """校验参数格式。"""
    if not agent or not agent.strip():
        print("错误: agentname 不能为空", file=sys.stderr)
        sys.exit(1)
    if not job or not job.strip():
        print("错误: jobname 不能为空", file=sys.stderr)
        sys.exit(1)
    if not re.fullmatch(r"[a-zA-Z0-9_]+", job):
        print(
            f"错误: jobname '{job}' 不符合规范，只允许英文字母、数字和下划线",
            file=sys.stderr,
        )
        sys.exit(1)


def get_worktree_dir(agent, job):
    """获取 worktree 目录路径。"""
    dirname = f"docs_all_{agent}_{job}"
    return MAIN_REPO.parent / dirname


def get_remote_repo(remote_name):
    """从 git remote URL 提取 OWNER/REPO 格式的仓库名。"""
    result = run_git("remote", "get-url", remote_name, check=False)
    url = result.stdout.strip()
    # 处理 git@github.com:OWNER/REPO.git 或 https://github.com/OWNER/REPO.git
    match = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if not match:
        return None
    return match.group(1)


def run_gh(*args, check=True):
    """执行 gh 命令。"""
    result = subprocess.run(
        ["gh"] + list(args),
        cwd=MAIN_REPO,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"警告: gh {' '.join(args)} 失败: {result.stderr.strip()}", file=sys.stderr)
    return result


def get_base_ref(upstream_branch=None):
    """获取最新上游代码的 ref，不影响主仓库工作区状态。

    优先 fetch upstream/main（fork 场景），否则 fetch origin/main。
    fork 场景下会用 gh repo sync 让远端 origin 也同步 upstream。
    如果指定了 upstream_branch，额外验证并同步该分支。
    返回可用于 worktree 创建的 ref 名。
    """
    remotes = run_git("remote", check=False).stdout.strip().splitlines()

    if "upstream" in remotes:
        print("从 upstream 拉取最新代码...")
        run_git("fetch", "upstream")

        # 用 gh repo sync 让 fork 远端也同步 upstream（main 分支）
        origin_repo = get_remote_repo("origin")
        upstream_repo = get_remote_repo("upstream")
        if origin_repo and upstream_repo:
            print(f"同步远端 fork main: {upstream_repo} -> {origin_repo} ...")
            run_gh("repo", "sync", origin_repo, "--source", upstream_repo)

            # 如果指定了上游分支，也同步该分支到 fork
            if upstream_branch:
                print(f"同步远端 fork 分支 {upstream_branch}: {upstream_repo} -> {origin_repo} ...")
                run_gh("repo", "sync", origin_repo, "--source", upstream_repo,
                       "--branch", upstream_branch)
        else:
            print("警告: 无法解析 remote URL，跳过远端同步", file=sys.stderr)

        # 更新本地的 origin/main remote tracking ref
        run_git("fetch", "upstream", "main:refs/remotes/origin/main", check=False)

        if upstream_branch:
            # 验证 upstream 上确实存在该分支
            ref_check = run_git(
                "ls-remote", "--heads", "upstream", upstream_branch, check=False
            )
            if not ref_check.stdout.strip():
                print(f"错误: upstream 上不存在分支 '{upstream_branch}'", file=sys.stderr)
                sys.exit(1)
            print(f"验证通过: upstream/{upstream_branch} 存在")
            # 更新本地 origin 的 tracking ref
            run_git(
                "fetch", "upstream",
                f"{upstream_branch}:refs/remotes/origin/{upstream_branch}",
                check=False,
            )
            return f"upstream/{upstream_branch}"

        return "upstream/main"
    else:
        print("从 origin 拉取最新代码...")
        run_git("fetch", "origin")

        if upstream_branch:
            ref_check = run_git(
                "ls-remote", "--heads", "origin", upstream_branch, check=False
            )
            if not ref_check.stdout.strip():
                print(f"错误: origin 上不存在分支 '{upstream_branch}'", file=sys.stderr)
                sys.exit(1)
            print(f"验证通过: origin/{upstream_branch} 存在")
            return f"origin/{upstream_branch}"

        return "origin/main"


def create_worktree(agent, job, upstream_branch=None):
    """创建文档工作区 worktree。"""
    branch = job
    worktree_dir = get_worktree_dir(agent, job)

    # 检查 worktree 是否已存在
    if worktree_dir.exists():
        print(f"错误: 工作区目录已存在: {worktree_dir}", file=sys.stderr)
        sys.exit(1)

    # 检查分支是否已存在
    branch_check = run_git("branch", "--list", branch, check=False)
    if branch_check.stdout.strip():
        print(f"错误: 分支 '{branch}' 已存在", file=sys.stderr)
        sys.exit(1)

    # 同步上游并获取基准 ref
    base_ref = get_base_ref(upstream_branch)

    # 创建 worktree（基于基准 ref 创建新分支）
    print(f"基于 {base_ref} 创建工作区分支 {branch} ...")
    run_git("worktree", "add", str(worktree_dir), "-b", branch, base_ref)

    # 返回结果
    result = {
        "status": "created",
        "worktree_dir": str(worktree_dir),
        "branch": branch,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _remove_worktree(worktree_dir, branch):
    """底层 worktree 删除：移除 worktree 目录 + 本地分支。"""
    run_git("worktree", "remove", str(worktree_dir), "--force")
    run_git("branch", "-D", branch)


def delete_worktree(agent, job):
    """删除文档工作区 worktree。"""
    branch = job
    worktree_dir = get_worktree_dir(agent, job)

    if not worktree_dir.exists():
        print(f"错误: 工作区目录不存在: {worktree_dir}", file=sys.stderr)
        sys.exit(1)

    _remove_worktree(worktree_dir, branch)

    result = {
        "status": "deleted",
        "worktree_dir": str(worktree_dir),
        "branch": branch,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _parse_worktree_list(output):
    """解析 git worktree list --porcelain 输出。"""
    worktrees = []
    current = {}
    for line in output.strip().splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            ref = line.split(" ", 1)[1]
            current["branch"] = ref.replace("refs/heads/", "")
    if current:
        worktrees.append(current)
    return worktrees


def save_clear():
    """安全清除已关闭PR对应的工作区、远端分支和预览目录。"""
    # 1. 拉取 ZEGOCLOUD/docs_all 最近一周的已关闭PR
    one_week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    print(f"查询 ZEGOCLOUD/docs_all 最近一周已关闭的PR...")

    result = run_gh(
        "pr", "list",
        "--repo", "ZEGOCLOUD/docs_all",
        "--state", "closed",
        "--json", "headRefName,number,title",
        "--search", f"closed:>={one_week_ago}",
        "--limit", "100",
    )

    if result.returncode != 0:
        print(f"错误: 查询PR失败", file=sys.stderr)
        sys.exit(1)

    closed_prs = json.loads(result.stdout) if result.stdout.strip() else []
    if not closed_prs:
        print("没有找到已关闭的PR")
        return

    pr_branches = {}
    for pr in closed_prs:
        head_ref = pr.get("headRefName", "")
        if head_ref:
            pr_branches[head_ref] = pr
            print(f"  PR #{pr.get('number')}: {head_ref} - {pr.get('title', '')}")

    # 2. 获取本地 worktree 列表
    wt_result = run_git("worktree", "list", "--porcelain")
    worktrees = _parse_worktree_list(wt_result.stdout)

    # 3. 匹配并清除
    cleaned = []
    for wt in worktrees:
        branch = wt.get("branch", "")
        wt_path = Path(wt["path"])

        # 跳过主仓库和不匹配的分支
        if wt_path.resolve() == MAIN_REPO.resolve() or branch not in pr_branches:
            continue

        wt_dirname = wt_path.name
        print(f"\n清理工作区: {wt_dirname} (分支: {branch})")

        # 删除 origin 远端分支
        print(f"  删除远端分支 origin/{branch}...")
        run_git("push", "origin", "--delete", branch, check=False)

        # 删除 docuo 构建目录
        docuo_dir = Path.home() / ".docuo" / f"{wt_dirname}-docuo-template"
        if docuo_dir.exists():
            print(f"  删除预览目录: {docuo_dir}")
            shutil.rmtree(docuo_dir)

        # 执行实际的 worktree 删除（本地分支 + worktree 目录）
        _remove_worktree(wt_path, branch)

        cleaned.append({
            "status": "deleted",
            "worktree_dir": str(wt_path),
            "branch": branch,
        })

    if not cleaned:
        print("没有匹配的工作区需要清理")
    else:
        print(f"\n共清理 {len(cleaned)} 个工作区:")
        for r in cleaned:
            print(json.dumps(r, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="文档工作区管理工具")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # create 子命令
    create_parser = subparsers.add_parser("create", help="创建工作区")
    create_parser.add_argument("--agent", required=True, help="agent 名称")
    create_parser.add_argument("--job", required=True, help="任务名称（仅英文下划线）")
    create_parser.add_argument("--branch", default=None, help="上游基准分支名（如 custom-video），不指定则基于 main")

    # delete 子命令
    delete_parser = subparsers.add_parser("delete", help="删除工作区")
    delete_parser.add_argument("--agent", default=None, help="agent 名称")
    delete_parser.add_argument("--job", default=None, help="任务名称（仅英文下划线）")
    delete_parser.add_argument("--save-clear", action="store_true",
                               help="安全清除已关闭PR的工作区（自动发现，无需 --agent/--job）")

    args = parser.parse_args()

    # 确保主仓库存在
    if not MAIN_REPO.exists():
        print(f"错误: 主仓库不存在: {MAIN_REPO}", file=sys.stderr)
        sys.exit(1)

    if args.action == "create":
        validate_params(args.agent, args.job)
        create_worktree(args.agent, args.job, getattr(args, "branch", None))
    elif args.action == "delete":
        if getattr(args, "save_clear", False):
            save_clear()
        else:
            if not args.agent or not args.job:
                print("错误: 需要 --agent 和 --job，或使用 --save-clear", file=sys.stderr)
                sys.exit(1)
            validate_params(args.agent, args.job)
            delete_worktree(args.agent, args.job)


if __name__ == "__main__":
    main()
