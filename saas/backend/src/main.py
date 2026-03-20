"""
SaaS Backend Core - FastAPI Application
Phase 3: Multi-tenant Agent OS
"""

from contextlib import asynccontextmanager

from api.v1.router import api_router, start_background_tasks
from core.config import settings
from core.database import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")

    # 启动后台快照缓存刷新任务
    start_background_tasks()
    print("✅ Background snapshot refresh task started (interval: 30s)")

    yield

    # 关闭时清理
    print("👋 Application shutting down")


# 创建FastAPI应用
app = FastAPI(
    title="OpenClaw Twins - API",
    description="Self-Monitoring & Self-Evolving Twin-Agent Platform",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "OpenClaw Twins Platform",
        "version": "3.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
