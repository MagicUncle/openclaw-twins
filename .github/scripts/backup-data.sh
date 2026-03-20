#!/bin/bash
# OpenClaw Twins - 数据备份脚本

set -e

BACKUP_DIR="data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="twins_backup_$TIMESTAMP"

usage() {
    echo "Usage: $0 [full|config|database]"
    echo "  full     - Backup everything"
    echo "  config   - Backup configuration only"
    echo "  database - Backup database only"
    exit 1
}

if [ $# -ne 1 ]; then
    usage
fi

BACKUP_TYPE=$1

mkdir -p $BACKUP_DIR

echo "🔄 Creating $BACKUP_TYPE backup..."

case $BACKUP_TYPE in
    full)
        echo "📦 Backing up everything..."
        tar -czf "$BACKUP_DIR/${BACKUP_NAME}_full.tar.gz" \
            src/twins/backend/ \
            src/agents/ \
            metrics/ \
            config/ \
            VERSION \
            2>/dev/null || true
        ;;
    config)
        echo "⚙️  Backing up configuration..."
        tar -czf "$BACKUP_DIR/${BACKUP_NAME}_config.tar.gz" \
            src/twins/backend/src/core/ \
            src/agents/*/config/ \
            VERSION \
            2>/dev/null || true
        ;;
    database)
        echo "🗄️  Backing up database..."
        if [ -f "data/*.db" ]; then
            cp data/*.db "$BACKUP_DIR/${BACKUP_NAME}_db/"
        fi
        ;;
    *)
        usage
        ;;
esac

echo "✅ Backup created: $BACKUP_DIR/${BACKUP_NAME}_*.tar.gz"
echo "📊 Backup size: $(du -h $BACKUP_DIR/${BACKUP_NAME}_*.tar.gz | cut -f1)"

# 清理旧备份（保留最近 30 天）
echo "🧹 Cleaning up old backups..."
find $BACKUP_DIR -name "twins_backup_*.tar.gz" -mtime +30 -delete
echo "✅ Cleanup complete"
