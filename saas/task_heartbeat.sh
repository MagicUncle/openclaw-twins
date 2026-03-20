#!/bin/bash
# Heartbeat Task Monitor - 任务完成确认心跳
# 每小时检查所有规划任务是否完成

echo "💓 OpenClaw Agent OS - 任务完成确认系统"
echo "=========================================="
echo "心跳周期: 1小时"
echo ""

# 任务清单
TASKS_FILE="/Users/magicuncle/.openclaw/workspace/TASK_CHECKLIST.md"

check_task() {
    local task_name=$1
    local check_command=$2
    
    echo -n "检查: $task_name ... "
    if eval "$check_command" > /dev/null 2>&1; then
        echo "✅ 完成"
        return 0
    else
        echo "❌ 未完成"
        return 1
    fi
}

# 主检查循环
check_all_tasks() {
    echo "📝 任务完成状态检查 ($(date '+%Y-%m-%d %H:%M:%S'))"
    echo ""
    
    local completed=0
    local total=0
    
    # 任务1: 数据可视化优化
    total=$((total + 1))
    if check_task "1. 数据可视化优化（人民币+解释）" \
        "grep -q 'toRMB' /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html"; then
        completed=$((completed + 1))
    fi
    
    # 任务2: 系统运行状态可视化
    total=$((total + 1))
    if check_task "2. 监控/导师Agent可视化" \
        "test -f /Users/magicuncle/.openclaw/workspace/agents/overseer/scripts/system_visualizer.py"; then
        completed=$((completed + 1))
    fi
    
    # 任务3: Staff菜单完整
    total=$((total + 1))
    if check_task "3. Staff菜单功能完整" \
        "grep -q 'StaffPage' /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html"; then
        completed=$((completed + 1))
    fi
    
    # 任务4: Budget菜单完整
    total=$((total + 1))
    if check_task "4. Budget菜单功能完整" \
        "grep -q 'BudgetPage' /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html"; then
        completed=$((completed + 1))
    fi
    
    # 任务5: Proposals菜单完整
    total=$((total + 1))
    if check_task "5. Proposals菜单功能完整" \
        "grep -q 'ProposalsPage' /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html"; then
        completed=$((completed + 1))
    fi
    
    # 任务6: 心跳改为1小时
    total=$((total + 1))
    if check_task "6. 心跳周期改为1小时" \
        "grep -q '3600000' /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html"; then
        completed=$((completed + 1))
    fi
    
    echo ""
    echo "=========================================="
    echo "📊 任务完成统计: $completed / $total"
    echo "=========================================="
    
    if [ $completed -eq $total ]; then
        echo "🎉 所有任务已完成！"
        return 0
    else
        echo "⏳ 还有 $((total - completed)) 个任务待完成"
        return 1
    fi
}

# 首次运行
check_all_tasks

# 每小时检查一次
echo ""
echo "进入监控模式，每小时自动检查..."
echo "按 Ctrl+C 退出"
echo ""

while true; do
    sleep 3600  # 1小时 = 3600秒
    clear
    echo "💓 心跳确认 ($(date '+%Y-%m-%d %H:%M:%S'))"
    echo "=========================================="
    check_all_tasks
done
