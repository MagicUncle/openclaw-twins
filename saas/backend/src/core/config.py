"""
Core Configuration
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "OpenClaw Agent OS SaaS"
    DEBUG: bool = True
    
    # 数据库（支持SQLite和PostgreSQL）
    DATABASE_URL: str = "sqlite:///./agent_os.db"  # 开发环境使用SQLite
    # DATABASE_URL: str = "postgresql://user:password@localhost/agent_os_saas"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # 租户配置
    DEFAULT_AGENT_QUOTA: int = 5
    DEFAULT_CALL_QUOTA: int = 1000
    
    class Config:
        env_file = ".env"


settings = Settings()
