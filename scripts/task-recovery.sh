#!/bin/bash
# Task Recovery System
# 检查并恢复中断的长任务

set -euo pipefail

WAL_DIR="${HOME}/.openclaw/wal"
RECOVERY_LOG="${HOME}/.openclaw/logs/task-recovery.log"

mkdir -p "$(dirname "$RECOVERY_LOG")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$RECOVERY_LOG"
}

# 检查活跃任务（运行超过30分钟的可能卡住了）
check_stalled_tasks() {
    log "Checking for stalled tasks..."
    
    local current_time=$(date +%s)
    local stalled_threshold=1800  # 30 minutes
    
    for wal_file in "$WAL_DIR/active"/*.json 2>/dev/null; do
        if [[ -f "$wal_file" ]]; then
            local start_time=$(python3 -c "
import json
import sys
try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
        from datetime import datetime
        start = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        print(int(start.timestamp()))
except Exception as e:
    print(0)
" 2>/dev/null || echo 0)
            
            if [[ "$start_time" -gt 0 ]]; then
                local elapsed=$((current_time - start_time))
                
                if [[ $elapsed -gt $stalled_threshold ]]; then
                    local task_id=$(python3 -c "import json; print(json.load(open('$wal_file'))['task_id'])")
                    local task_type=$(python3 -c "import json; print(json.load(open('$wal_file'))['task_type'])")
                    
                    log "⚠️ Stalled task detected: $task_type/$task_id (${elapsed}s elapsed)"
                    
                    # 输出恢复建议
                    echo ""
                    echo "🔄 Recovery Candidate:"
                    echo "  Task: $task_type - $task_id"
                    echo "  Running for: $((elapsed / 60)) minutes"
                    echo "  WAL File: $wal_file"
                    
                    # 显示最后进度
                    python3 << PYEOF
import json
try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    if 'progress' in data and data['progress']:
        last_progress = data['progress'][-1]
        print(f"  Last Step: {last_progress.get('step', 'N/A')}")
        print(f"  Message: {last_progress.get('message', 'N/A')}")
        print(f"  Progress: {last_progress.get('percent', 'N/A')}%")
    else:
        print("  No progress recorded yet")
except Exception as e:
    print(f"  Error reading progress: {e}")
PYEOF
                    
                    echo ""
                    echo "  💡 To recover, run:"
                    echo "     wal-system.sh recover $task_id"
                    echo ""
                fi
            fi
        fi
    done
}

# 列出可恢复的任务
list_recoverable() {
    log "Listing recoverable tasks..."
    
    echo ""
    echo "📋 Recoverable Tasks:"
    echo "===================="
    
    # 活跃任务
    for wal_file in "$WAL_DIR/active"/*.json 2>/dev/null; do
        if [[ -f "$wal_file" ]]; then
            python3 << PYEOF
import json
try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    print(f"[ACTIVE] {data['task_type']}/{data['task_id']}")
    print(f"         Started: {data['start_time']}")
    if 'progress' in data and data['progress']:
        last = data['progress'][-1]
        print(f"         Last: {last['step']} ({last.get('percent', 'N/A')}%)")
    print("")
except Exception as e:
    pass
PYEOF
        fi
    done
    
    # 失败任务（最近24小时）
    for wal_file in "$WAL_DIR/failed"/*.json 2>/dev/null; do
        if [[ -f "$wal_file" ]]; then
            local mtime=$(stat -f%m "$wal_file" 2>/dev/null || stat -c%Y "$wal_file" 2>/dev/null || echo 0)
            local current=$(date +%s)
            
            if [[ $((current - mtime)) -lt 86400 ]]; then
                python3 << PYEOF
import json
try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    print(f"[FAILED] {data['task_type']}/{data['task_id']}")
    print(f"         Failed at: {data.get('end_time', 'Unknown')}")
    if 'progress' in data and data['progress']:
        last = data['progress'][-1]
        print(f"         Last successful step: {last['step']}")
    print("")
except Exception as e:
    pass
PYEOF
            fi
        fi
    done
}

# 自动恢复建议
suggest_recovery() {
    local task_id="$1"
    
    # 查找任务
    local wal_file=""
    for file in "$WAL_DIR/active"/*.json "$WAL_DIR/failed"/*.json 2>/dev/null; do
        if [[ -f "$file" ]]; then
            local tid=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('task_id',''))" 2>/dev/null || echo "")
            if [[ "$tid" == "$task_id" ]]; then
                wal_file="$file"
                break
            fi
        fi
    done
    
    if [[ -z "$wal_file" ]]; then
        echo "❌ Task not found: $task_id"
        return 1
    fi
    
    echo "📊 Task Analysis:"
    echo "================"
    
    python3 << PYEOF
import json

try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    print(f"Task: {data['task_type']} - {data['task_id']}")
    print(f"Description: {data.get('description', 'N/A')}")
    print(f"Status: {data['status']}")
    print(f"Started: {data['start_time']}")
    
    if 'end_time' in data:
        print(f"Ended: {data['end_time']}")
    
    print("\n📈 Progress History:")
    if 'progress' in data and data['progress']:
        for i, p in enumerate(data['progress'][-5:], 1):  # Show last 5
            print(f"  {i}. {p['step']}: {p['message']} ({p.get('percent', 'N/A')}%)")
    else:
        print("  No progress recorded")
    
    print("\n💡 Recovery Options:")
    print("  1. Resume from last step")
    print("  2. Restart from beginning")
    print("  3. Mark as completed manually")
    print("  4. Archive and start new task")
    
except Exception as e:
    print(f"Error: {e}")
PYEOF
}

# 主命令
case "${1:-}" in
    check)
        check_stalled_tasks
        ;;
    list)
        list_recoverable
        ;;
    suggest)
        suggest_recovery "$2"
        ;;
    *)
        echo "Task Recovery System"
        echo "===================="
        echo ""
        echo "Usage: $0 {check|list|suggest}"
        echo ""
        echo "Commands:"
        echo "  check          - Check for stalled tasks"
        echo "  list           - List all recoverable tasks"
        echo "  suggest <id>  - Suggest recovery options for task"
        echo ""
        
        # 默认执行 check
        check_stalled_tasks
        ;;
esac
