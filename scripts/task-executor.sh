#!/bin/bash
# Task Executor Wrapper with WAL (Write-Ahead Logging)
# 统一任务执行包装器，解决环境变量和日志问题

set -euo pipefail

# 配置
TASK_NAME="$1"
SCRIPT_PATH="$2"
LOG_DIR="$HOME/.openclaw/logs/tasks"
WAL_DIR="$HOME/.openclaw/wal"

# 创建目录
mkdir -p "$LOG_DIR" "$WAL_DIR"

# 时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/${TASK_NAME}_${TIMESTAMP}.log"
WAL_FILE="$WAL_DIR/${TASK_NAME}_${TIMESTAMP}.wal"

# WAL: 记录任务开始
{
    echo "{"
    echo "  \"task\": \"$TASK_NAME\","
    echo "  \"script\": \"$SCRIPT_PATH\","
    echo "  \"start_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"status\": \"RUNNING\","
    echo "  \"pid\": $$"
    echo "}"
} > "$WAL_FILE"

# 设置环境变量（解决 cron 环境缺失问题）
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
export HOME="$HOME"
export USER="$USER"
export SHELL="/bin/bash"

# 代理设置
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

# OpenClaw 特定环境
export OPENCLAW_WORKSPACE="$HOME/.openclaw/workspace"

# 日志头
{
    echo "========================================"
    echo "Task: $TASK_NAME"
    echo "Script: $SCRIPT_PATH"
    echo "Start: $(date)"
    echo "PID: $$"
    echo "PWD: $(pwd)"
    echo "PATH: $PATH"
    echo "========================================"
} | tee -a "$LOG_FILE"

# 执行脚本
echo "[$(date +%H:%M:%S)] Starting execution..." | tee -a "$LOG_FILE"

EXIT_CODE=0
if bash "$SCRIPT_PATH" >> "$LOG_FILE" 2>&1; then
    echo "[$(date +%H:%M:%S)] ✓ Execution completed successfully" | tee -a "$LOG_FILE"
    STATUS="COMPLETED"
else
    EXIT_CODE=$?
    echo "[$(date +%H:%M:%S)] ✗ Execution failed with code $EXIT_CODE" | tee -a "$LOG_FILE"
    STATUS="FAILED"
fi

# WAL: 记录任务结束
{
    echo "{"
    echo "  \"task\": \"$TASK_NAME\","
    echo "  \"script\": \"$SCRIPT_PATH\","
    echo "  \"start_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"end_time\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
    echo "  \"status\": \"$STATUS\","
    echo "  \"exit_code\": $EXIT_CODE,"
    echo "  \"log_file\": \"$LOG_FILE\","
    echo "  \"wal_file\": \"$WAL_FILE\""
    echo "}"
} > "${WAL_FILE}.done"

# 清理旧 WAL 文件（保留最近 30 天）
find "$WAL_DIR" -name "*.wal" -mtime +30 -delete 2>/dev/null || true
find "$WAL_DIR" -name "*.wal.done" -mtime +30 -delete 2>/dev/null || true

# 清理旧日志（保留最近 7 天）
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true

echo "[$(date +%H:%M:%S)] Task $STATUS" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"

exit $EXIT_CODE
