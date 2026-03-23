#!/bin/bash
# Cleanup merged translation workspaces
# Usage: run from cron, outputs JSON summary

TRANSLATION_DIR="/home/oliver/code/translation"
SUMMARY_FILE="/tmp/translation_cleanup_summary.txt"

rm -f "$SUMMARY_FILE"

if [ ! -d "$TRANSLATION_DIR" ]; then
    echo "NO_WORKSPACES:translation目录不存在" > "$SUMMARY_FILE"
    exit 0
fi

cd "$TRANSLATION_DIR"
dirs=(docs_all_translate_*)

if [ ! -d "${dirs[0]}" ]; then
    echo "NO_WORKSPACES:没有待检查的翻译工作区" > "$SUMMARY_FILE"
    exit 0
fi

merged=()
not_merged=()
errors=()

for dir in "${dirs[@]}"; do
    [ -d "$dir" ] || continue
    cd "$TRANSLATION_DIR/$dir"

    branch=$(git branch --show-current 2>/dev/null)
    if [ -z "$branch" ] || [ "$branch" = "main" ]; then
        errors+=("$dir: 无法确定分支名")
        continue
    fi

    # Check if PR exists and is merged
    pr_state=$(gh pr list \
        --repo ZEGOCLOUD/docs_all \
        --head "DavidRelo:$branch" \
        --json state --jq '.[0].state' 2>/dev/null)

    if [ "$pr_state" = "MERGED" ]; then
        merged+=("$dir (分支: $branch)")
        rm -rf "$TRANSLATION_DIR/$dir"
    elif [ "$pr_state" = "CLOSED" ]; then
        merged+=("$dir (分支: $branch, PR已关闭)")
        rm -rf "$TRANSLATION_DIR/$dir"
    elif [ -z "$pr_state" ]; then
        # No PR found, check if commits are in upstream/main
        git fetch upstream main --quiet 2>/dev/null
        if git merge-base --is-ancestor HEAD upstream/main 2>/dev/null; then
            merged+=("$dir (分支: $branch, 提交已包含在上游)")
            rm -rf "$TRANSLATION_DIR/$dir"
        else
            not_merged+=("$dir (分支: $branch, 未找到PR)")
        fi
    else
        not_merged+=("$dir (分支: $branch, PR状态: $pr_state)")
    fi

    cd "$TRANSLATION_DIR"
done

{
    echo "=== 翻译工作区清理报告 ==="
    echo "时间: $(date '+%Y-%m-%d %H:%M')"
    echo ""
    echo "✅ 已清理 (${#merged[@]}):"
    if [ ${#merged[@]} -eq 0 ]; then echo "  (无)"; else printf '  - %s\n' "${merged[@]}"; fi
    echo ""
    echo "⏳ 未合并 (${#not_merged[@]}):"
    if [ ${#not_merged[@]} -eq 0 ]; then echo "  (无)"; else printf '  - %s\n' "${not_merged[@]}"; fi
    echo ""
    echo "⚠️ 异常 (${#errors[@]}):"
    if [ ${#errors[@]} -eq 0 ]; then echo "  (无)"; else printf '  - %s\n' "${errors[@]}"; fi
} > "$SUMMARY_FILE"
