"""
Pydantic Schemas for API
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ============== Tenant Schemas ==============

class TenantBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None


class TenantCreate(TenantBase):
    slug: str


class TenantResponse(TenantBase):
    id: str
    slug: str
    status: str
    plan: str
    max_agents: int
    max_calls_per_month: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== User Schemas ==============

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str
    tenant_id: str
    role: str = "developer"


class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool
    tenant_id: str
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ============== Agent Schemas ==============

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str = "custom"


class AgentCreate(AgentBase):
    config: Optional[dict] = None


class AgentResponse(AgentBase):
    id: str
    status: str
    is_active: bool
    total_calls: int
    success_rate: int
    tenant_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AgentStats(BaseModel):
    total_calls: int
    success_rate: float
    avg_duration_ms: Optional[int] = None
    total_tokens: int


# ============== Proposal Schemas ==============

class ProposalBase(BaseModel):
    title: str
    description: Optional[str] = None
    proposal_type: str
    priority: str = "P2"


class ProposalResponse(ProposalBase):
    id: str
    status: str
    content: Optional[dict] = None
    tenant_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== Dashboard Schemas ==============

class DashboardStats(BaseModel):
    total_agents: int
    total_calls_today: int
    success_rate: float
    active_proposals: int


class AgentRanking(BaseModel):
    id: str
    name: str
    efficiency_score: float
    success_rate: float
    grade: str
    calls: int


class DashboardResponse(BaseModel):
    stats: DashboardStats
    agent_rankings: List[AgentRanking]
    recent_proposals: List[ProposalResponse]
