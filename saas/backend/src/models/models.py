"""
Data Models - User & Tenant
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


class UserRole(str, enum.Enum):
    """用户角色"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class TenantStatus(str, enum.Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class PlanType(str, enum.Enum):
    """套餐类型"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    """租户模型 - SaaS多租户核心"""
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(Enum(TenantStatus), default=TenantStatus.TRIAL)
    plan = Column(Enum(PlanType), default=PlanType.FREE)
    
    # 配额限制
    max_agents = Column(Integer, default=5)
    max_calls_per_month = Column(Integer, default=1000)
    
    # 联系信息
    email = Column(String(255))
    phone = Column(String(50))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 关系
    users = relationship("User", back_populates="tenant")
    agents = relationship("Agent", back_populates="tenant")
    
    def __repr__(self):
        return f"<Tenant {self.name}>"


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # 个人信息
    first_name = Column(String(50))
    last_name = Column(String(50))
    
    # 角色与状态
    role = Column(Enum(UserRole), default=UserRole.DEVELOPER)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # 租户关联
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")
    
    # API密钥
    api_key = Column(String(64), unique=True, index=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<User {self.email}>"


class Agent(Base):
    """Agent模型 - 多租户隔离"""
    __tablename__ = "agents"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    agent_type = Column(String(50), default="custom")
    
    # 配置（JSON存储）
    config = Column(Text)  # JSON字符串
    
    # 状态
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default="idle")
    
    # 统计
    total_calls = Column(Integer, default=0)
    success_rate = Column(Integer, default=100)  # 百分比
    
    # 租户关联
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="agents")
    
    # 创建者
    created_by = Column(String(36), ForeignKey("users.id"))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Agent {self.name}>"


class AgentCall(Base):
    """Agent调用记录 - 用于计费和监控"""
    __tablename__ = "agent_calls"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"))
    
    # 调用详情
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer)
    status = Column(String(20))  # success, failure, timeout
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Proposal(Base):
    """Architect生成的优化提案"""
    __tablename__ = "proposals"
    
    id = Column(String(100), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    proposal_type = Column(String(50))  # optimization, new_skill
    
    # 状态
    status = Column(String(20), default="pending")  # pending, approved, rejected, applied
    priority = Column(String(10), default="P2")  # P0, P1, P2
    
    # 内容（JSON）
    content = Column(Text)  # JSON字符串
    
    # 租户关联
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    applied_at = Column(DateTime(timezone=True))
