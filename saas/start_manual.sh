#!/bin/bash
# 手动启动方案（无需Docker）

echo "🚀 OpenClaw Agent OS SaaS - 手动启动"
echo "======================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

echo "✅ Python3已安装"

# 创建Python虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -q fastapi uvicorn sqlalchemy pydantic python-jose passlib

# 创建SQLite数据库（简化版，无需PostgreSQL）
echo "🗄️  初始化SQLite数据库..."
python3 << 'EOF'
import sys
sys.path.insert(0, 'backend/src')

from sqlalchemy import create_engine
from core.database import Base

# 使用SQLite代替PostgreSQL
engine = create_engine('sqlite:///./agent_os.db', echo=False)
Base.metadata.create_all(bind=engine)
print("✅ 数据库表创建完成")
EOF

# 启动后端（后台）
echo "🔌 启动后端服务..."
cd backend/src
export DATABASE_URL="sqlite:///../../agent_os.db"
export SECRET_KEY="dev-secret-key"
export DEBUG="true"

# 使用nohup后台运行
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../../backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

echo "✅ 后端已启动 (PID: $BACKEND_PID)"
echo "   日志: backend.log"

# 等待后端启动
sleep 3

# 启动前端（使用Python简单HTTP服务器）
echo "🌐 启动前端服务..."
cd frontend/public
nohup python3 -m http.server 3000 > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

echo "✅ 前端已启动 (PID: $FRONTEND_PID)"
echo "   日志: frontend.log"

echo ""
echo "=========================================="
echo "🎉 服务启动完成！"
echo "=========================================="
echo ""
echo "🌐 访问地址:"
echo "  • Dashboard: http://localhost:3000"
echo "  • API文档:   http://localhost:8000/docs"
echo "  • API端点:   http://localhost:8000/api/v1"
echo ""
echo "📝 日志文件:"
echo "  • 后端: backend.log"
echo "  • 前端: frontend.log"
echo ""
echo "🛑 停止服务:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""

# 保存PID
echo "$BACKEND_PID $FRONTEND_PID" > .pids
