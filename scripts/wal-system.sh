#!/bin/bash
# WAL (Write-Ahead Logging) System for OpenClaw
# 操作前日志系统，支持任务恢复和状态追踪

set -euo pipefail

WAL_BASE_DIR="${HOME}/.openclaw/wal"
mkdir -p "$WAL_BASE_DIR"/{active,completed,failed}

# 函数：开始任务
wal_start() {
    local task_id="$1"
    local task_type="$2"
    local description="$3"
    local script_path="${4:-}"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local wal_id="${task_type}_${timestamp}_${task_id}"
    local wal_file="$WAL_BASE_DIR/active/${wal_id}.json"
    
    mkdir -p "$(dirname "$wal_file")"
    
    cat > "$wal_file" << EOF
{
  "wal_id": "$wal_id",
  "task_id": "$task_id",
  "task_type": "$task_type",
  "description": "$description",
  "script_path": "$script_path",
  "status": "RUNNING",
  "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hostname": "$(hostname)",
  "pid": $$
}
EOF
    
    echo "$wal_file"
}

# 函数：更新任务进度
wal_progress() {
    local wal_file="$1"
    local step="$2"
    local message="$3"
    local percent="${4:-}"
    
    if [[ ! -f "$wal_file" ]]; then
        echo "Error: WAL file not found: $wal_file" >&2
        return 1
    fi
    
    # 读取现有 WAL
    local temp_file="${wal_file}.tmp"
    
    # 添加进度记录
    local progress_entry="{\"step\": \"$step\", \"message\": \"$message\", \"percent\": \"$percent\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
    
    # 使用 Python 更新 JSON（更可靠）
    python3 << PYEOF
import json
import sys

try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    if 'progress' not in data:
        data['progress'] = []
    
    data['progress'].append({
        'step': '$step',
        'message': '$message',
        'percent': '$percent',
        'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
    })
    data['last_update'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
    
    with open('$temp_file', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("OK")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    
    if [[ $? -eq 0 ]]; then
        mv "$temp_file" "$wal_file"
    fi
}

# 函数：完成任务
wal_complete() {
    local wal_file="$1"
    local result="${2:-success}"
    local output_summary="${3:-}"
    
    if [[ ! -f "$wal_file" ]]; then
        return 1
    fi
    
    local wal_id=$(basename "$wal_file" .json)
    local target_dir="$WAL_BASE_DIR/completed"
    [[ "$result" == "failed" ]] && target_dir="$WAL_BASE_DIR/failed"
    
    mkdir -p "$target_dir"
    
    # 更新状态
    python3 << PYEOF
import json
import sys

try:
    with open('$wal_file', 'r') as f:
        data = json.load(f)
    
    data['status'] = '${result^^}'
    data['end_time'] = '$(date -u +%Y-%m-%dT%H:%M:%SZ)'
    data['output_summary'] = '''$output_summary'''
    data['duration_seconds'] = $(($(date +%s) - $(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$(python3 -c "import json; print(json.load(open('$wal_file'))['start_time'])")" +%s 2>/dev/null || echo $(date +%s))))
    
    target_file = '$target_dir/${wal_id}.json'
    with open(target_file, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(target_file)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    
    # 删除 active 文件
    rm -f "$wal_file"
}

# 函数：列出活跃任务
wal_list_active() {
    echo "Active Tasks:"
    echo "============="
    
    for file in "$WAL_BASE_DIR/active"/*.json 2>/dev/null; do
        if [[ -f "$file" ]]; then
            local task_id=$(python3 -c "import json; print(json.load(open('$file'))['task_id'])")
            local task_type=$(python3 -c "import json; print(json.load(open('$file'))['task_type'])")
            local status=$(python3 -c "import json; print(json.load(open('$file'))['status'])")
            local start_time=$(python3 -c "import json; print(json.load(open('$file'))['start_time'])")
            echo "  - $task_type/$task_id ($status) since $start_time"
        fi
    done
}

# 函数：恢复任务（查看中断的任务）
wal_recover() {
    local task_id="$1"
    
    # 查找最近的中断任务
    local found_file=""
    for file in "$WAL_BASE_DIR/active"/*.json "$WAL_BASE_DIR/failed"/*.json 2>/dev/null; do
        if [[ -f "$file" ]]; then
            local tid=$(python3 -c "import json; d=json.load(open('$file')); print(d.get('task_id',''))" 2>/dev/null)
            if [[ "$tid" == "$task_id" ]]; then
                found_file="$file"
                break
            fi
        fi
    done
    
    if [[ -z "$found_file" ]]; then
        echo "No task found with ID: $task_id"
        return 1
    fi
    
    echo "Found task: $found_file"
    python3 -c "import json; import sys; json.dump(json.load(open('$found_file')), sys.stdout, indent=2, ensure_ascii=False)"
}

# 主命令
case "${1:-}" in
    start)
        wal_start "$2" "$3" "$4" "${5:-}"
        ;;
    progress)
        wal_progress "$2" "$3" "$4" "${5:-}"
        ;;
    complete)
        wal_complete "$2" "${3:-success}" "${4:-}"
        ;;
    list)
        wal_list_active
        ;;
    recover)
        wal_recover "$2"
        ;;
    *)
        echo "Usage: $0 {start|progress|complete|list|recover}"
        echo "  start <task_id> <type> <description> [script]"
        echo "  progress <wal_file> <step> <message> [percent]"
        echo "  complete <wal_file> [success|failed] [summary]"
        echo "  list"
        echo "  recover <task_id>"
        exit 1
        ;;
esac
