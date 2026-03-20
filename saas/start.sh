#!/bin/bash
# OpenClaw Agent OS SaaS - 快速启动脚本

echo "🚀 OpenClaw Agent OS SaaS - Phase 3 启动器"
echo "=========================================="

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装"
    exit 1
fi

echo ""
echo "📦 启动服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 5

echo ""
echo "✅ 服务状态:"
docker-compose ps

echo ""
echo "🌐 访问地址:"
echo "  - Dashboard: http://localhost:3000"
echo "  - API文档: http://localhost:8000/docs"
echo "  - API端点: http://localhost:8000/api/v1"
echo ""
echo "🔧 管理命令:"
echo "  - 查看日志: docker-compose logs -f"
echo "  - 停止服务: docker-compose down"
echo "  - 重启服务: docker-compose restart"
echo ""
echo "📚 文档: ./docs/README.md"
