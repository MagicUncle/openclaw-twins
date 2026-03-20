#!/bin/bash
# OpenClaw Twins - 数据还原脚本

set -e

BACKUP_DIR="data/backups"

usage() {
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -1t $BACKUP_DIR/*.tar.gz 2>/dev/null | head -10 || echo "  (none)"
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    # 尝试从备份目录查找
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "❌ Backup file not found: $1"
        exit 1
    fi
fi

echo "🔄 Restoring from: $BACKUP_FILE"
echo "⚠️  This will overwrite current data. Continue? (y/N)"
read -r confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Aborted"
    exit 1
fi

# 创建当前状态备份
echo "📦 Creating safety backup of current state..."
SAFETY_BACKUP="$BACKUP_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$SAFETY_BACKUP" \
    src/twins/backend/ \
    src/agents/ \
    metrics/ \
    2>/dev/null || true
echo "✅ Safety backup: $SAFETY_BACKUP"

# 解压还原
echo "📂 Extracting backup..."
tar -xzf "$BACKUP_FILE" -C .
echo "✅ Restore complete"

# 验证
echo "🔍 Verifying..."
if [ -f "VERSION" ]; then
    echo "📋 Version: $(cat VERSION)"
fi

echo ""
echo "🎉 Restore completed successfully!"
echo "   Start the services with: make start"
