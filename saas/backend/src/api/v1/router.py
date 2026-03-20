"""
API Routes v1
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import asyncio
import json
import time

from core.database import get_db
from services.auth import AuthService, get_current_active_user
from models.models import User, Tenant, Agent, Proposal
from models import schemas


api_router = APIRouter()

# ============== 快照缓存（30秒刷新）==============

_snapshot_cache = {
    "data": None,
    "updated_at": 0.0,
    "lock": None,           # asyncio.Lock，在首次使用时初始化
}
_SSE_CLIENTS: list = []     # 订阅 SSE 的客户端队列列表
CACHE_TTL = 30              # 秒


def _get_lock():
    if _snapshot_cache["lock"] is None:
        _snapshot_cache["lock"] = asyncio.Lock()
    return _snapshot_cache["lock"]


async def _build_snapshot() -> dict:
    """调用 FullDataCollector 生成快照，返回 dict"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
    from full_data_collector import FullDataCollector

    def _run():
        collector = FullDataCollector()
        snapshot = collector.get_full_snapshot()
        return {
            "generated_at": snapshot.generated_at,
            "sessions": {
                "count": snapshot.session_count,
                "active": snapshot.active_sessions,
                "blocked": snapshot.blocked_sessions,
                "error": snapshot.error_sessions,
                "details": [{
                    "session_key": s.session_key,
                    "label": s.label,
                    "agent_id": s.agent_id,
                    "state": s.state.value,
                    "model": s.model,
                    "tokens_in": s.tokens_in,
                    "tokens_out": s.tokens_out,
                    "tokens_total": s.tokens_in + s.tokens_out,
                    "cost": s.cost,
                    "message_count": s.message_count,
                    "tool_calls": s.tool_calls,
                    "errors": s.errors,
                    "waiting_approvals": s.waiting_approvals,
                    "duration_minutes": s.duration_minutes,
                    "last_message_at": s.last_message_at,
                } for s in snapshot.sessions],
            },
            "approvals": {
                "pending": snapshot.pending_approvals,
                "approved": snapshot.approved_count,
                "denied": snapshot.denied_count,
                "details": [{
                    "approval_id": a.approval_id,
                    "agent_id": a.agent_id,
                    "status": a.status,
                    "command": a.command,
                    "reason": a.reason,
                    "requested_at": a.requested_at,
                } for a in snapshot.approvals],
            },
            "budget": {
                "total_scopes": snapshot.total_budget_scopes,
                "over_count": snapshot.over_budget_count,
                "warn_count": snapshot.warn_budget_count,
                "total_cost": snapshot.total_estimated_cost,
                "metrics": [{
                    "scope": b.scope,
                    "scope_id": b.scope_id,
                    "used": b.used,
                    "limit": b.limit,
                    "usage_percent": b.usage_percent,
                    "status": b.status,
                    "estimated_cost": b.estimated_cost,
                } for b in snapshot.budget_metrics],
            },
            "tasks": {
                "total": snapshot.total_tasks,
                "todo": snapshot.todo_count,
                "in_progress": snapshot.in_progress_count,
                "blocked": snapshot.blocked_count,
                "done": snapshot.done_count,
                "details": [{
                    "task_id": t.task_id,
                    "title": t.title,
                    "status": t.status,
                    "owner": t.owner,
                    "project": t.project_title,
                    "artifacts": t.artifacts_count,
                } for t in snapshot.tasks],
            },
            "projects": [{
                "project_id": p.project_id,
                "title": p.title,
                "status": p.status,
                "owner": p.owner,
                "total_tasks": p.total_tasks,
                "in_progress": p.in_progress,
                "blocked": p.blocked,
                "done": p.done,
            } for p in snapshot.projects],
            "alerts": {
                "total": len(snapshot.alerts),
                "info": snapshot.info_alerts,
                "warn": snapshot.warn_alerts,
                "action_required": snapshot.action_required_alerts,
                "items": [{
                    "level": a.level.value,
                    "code": a.code,
                    "message": a.message,
                    "source": a.source,
                    "count": a.count,
                } for a in snapshot.alerts],
            },
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run)


async def _refresh_cache(force: bool = False):
    """刷新缓存，如果距上次刷新 < CACHE_TTL 且 force=False 则跳过"""
    now = time.monotonic()
    if not force and _snapshot_cache["data"] is not None:
        if now - _snapshot_cache["updated_at"] < CACHE_TTL:
            return

    async with _get_lock():
        # double-check inside lock
        now = time.monotonic()
        if not force and _snapshot_cache["data"] is not None:
            if now - _snapshot_cache["updated_at"] < CACHE_TTL:
                return
        try:
            data = await _build_snapshot()
            _snapshot_cache["data"] = data
            _snapshot_cache["updated_at"] = time.monotonic()
            # 推送 SSE 事件给所有订阅客户端
            event = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            dead = []
            for q in _SSE_CLIENTS:
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                try:
                    _SSE_CLIENTS.remove(q)
                except ValueError:
                    pass
        except Exception as e:
            print(f"[cache] refresh failed: {e}")


async def _background_refresh():
    """后台任务：每 CACHE_TTL 秒刷新一次缓存"""
    while True:
        await asyncio.sleep(CACHE_TTL)
        await _refresh_cache(force=True)


def start_background_tasks():
    """由 lifespan 调用，启动后台刷新任务"""
    loop = asyncio.get_event_loop()
    loop.create_task(_background_refresh())


# ============== Auth Routes ==============

@api_router.post("/auth/login", response_model=schemas.Token)
async def login(
    credentials: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录"""
    auth_service = AuthService(db)
    token = auth_service.login(credentials.email, credentials.password)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    return token


@api_router.get("/auth/me", response_model=schemas.UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


# ============== Tenant Routes ==============

@api_router.get("/tenants", response_model=List[schemas.TenantResponse])
async def list_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取租户列表（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not authorized")

    tenants = db.query(Tenant).all()
    return tenants


@api_router.get("/tenants/{tenant_id}", response_model=schemas.TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取租户详情"""
    # 只能查看自己的租户（除非是超管）
    if not current_user.is_superuser and current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return tenant


# ============== Agent Routes ==============

@api_router.get("/agents", response_model=List[schemas.AgentResponse])
async def list_agents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取Agent列表（自动过滤当前租户）"""
    agents = db.query(Agent).filter(
        Agent.tenant_id == current_user.tenant_id
    ).all()
    return agents


@api_router.post("/agents", response_model=schemas.AgentResponse)
async def create_agent(
    agent_data: schemas.AgentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建Agent"""
    # 检查配额
    agent_count = db.query(Agent).filter(
        Agent.tenant_id == current_user.tenant_id
    ).count()

    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if agent_count >= tenant.max_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Agent quota exceeded (max: {tenant.max_agents})"
        )

    # 创建Agent
    import uuid
    new_agent = Agent(
        id=str(uuid.uuid4()),
        name=agent_data.name,
        description=agent_data.description,
        agent_type=agent_data.agent_type,
        config=str(agent_data.config) if agent_data.config else None,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id
    )

    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    return new_agent


@api_router.get("/agents/{agent_id}", response_model=schemas.AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取Agent详情"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.tenant_id == current_user.tenant_id
    ).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


# ============== Proposal Routes ==============

@api_router.get("/proposals", response_model=List[schemas.ProposalResponse])
async def list_proposals(
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取提案列表"""
    query = db.query(Proposal).filter(
        Proposal.tenant_id == current_user.tenant_id
    )

    if status:
        query = query.filter(Proposal.status == status)

    proposals = query.order_by(Proposal.created_at.desc()).all()
    return proposals





# ============== Dashboard Routes ==============

@api_router.get("/dashboard/stats", response_model=schemas.DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取Dashboard统计数据"""
    tenant_id = current_user.tenant_id

    # Agent数量
    total_agents = db.query(Agent).filter(
        Agent.tenant_id == tenant_id
    ).count()

    # TODO: 实现真实的调用统计
    # 这里简化处理

    return schemas.DashboardStats(
        total_agents=total_agents,
        total_calls_today=0,
        success_rate=100.0,
        active_proposals=0
    )


@api_router.get("/dashboard/rankings", response_model=List[schemas.AgentRanking])
async def get_agent_rankings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取Agent排名"""
    agents = db.query(Agent).filter(
        Agent.tenant_id == current_user.tenant_id
    ).all()

    rankings = []
    for agent in agents:
        rankings.append(schemas.AgentRanking(
            id=agent.id,
            name=agent.name,
            efficiency_score=agent.success_rate / 10.0,
            success_rate=agent.success_rate / 100.0,
            grade="B",
            calls=agent.total_calls
        ))

    return sorted(rankings, key=lambda x: x.efficiency_score, reverse=True)


# ============== Budget Config API ==============

@api_router.get("/budget/config")
async def get_budget_config(
    current_user: User = Depends(get_current_active_user)
):
    """获取预算配置（全局默认 + 各 Agent 手动覆盖）"""
    import json
    from pathlib import Path
    config_path = Path.home() / ".openclaw" / "workspace" / "metrics" / "budget_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "global_default_limit": 100000,
        "dynamic_adjustment": {"enabled": True},
        "agent_overrides": {}
    }


@api_router.put("/budget/config/agent/{agent_id}")
async def update_agent_budget(
    agent_id: str,
    body: dict,
    current_user: User = Depends(get_current_active_user)
):
    """手动设置单个 Agent 的 Token 配额"""
    import json
    from pathlib import Path
    from datetime import datetime

    config_path = Path.home() / ".openclaw" / "workspace" / "metrics" / "budget_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {
            "version": 1,
            "global_default_limit": 100000,
            "dynamic_adjustment": {"enabled": True},
            "agent_overrides": {}
        }

    new_limit = int(body.get("limit", 100000))
    manual = bool(body.get("manual_override", True))
    note = str(body.get("note", ""))

    if "agent_overrides" not in cfg:
        cfg["agent_overrides"] = {}

    cfg["agent_overrides"][agent_id] = {
        "limit": new_limit,
        "manual_override": manual,
        "note": note,
        "updated_at": datetime.now().isoformat()
    }
    cfg["updated_at"] = datetime.now().isoformat()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    # 强制刷新快照缓存
    import asyncio
    asyncio.create_task(_refresh_cache(force=True))

    return {"message": f"Budget for {agent_id} updated", "agent_id": agent_id, "limit": new_limit}


@api_router.put("/budget/config/dynamic")
async def update_dynamic_config(
    body: dict,
    current_user: User = Depends(get_current_active_user)
):
    """开启/关闭动态预算调整"""
    import json
    from pathlib import Path
    from datetime import datetime

    config_path = Path.home() / ".openclaw" / "workspace" / "metrics" / "budget_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {"version": 1, "global_default_limit": 100000, "dynamic_adjustment": {}, "agent_overrides": {}}

    cfg["dynamic_adjustment"]["enabled"] = bool(body.get("enabled", True))
    cfg["updated_at"] = datetime.now().isoformat()

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    return {"message": "Dynamic config updated", "enabled": cfg["dynamic_adjustment"]["enabled"]}


# ============== Full System Snapshot API (cached, near-realtime) ==============

@api_router.get("/system/snapshot")
async def get_full_system_snapshot(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取完整系统快照。
    结果缓存 30 秒，后台自动刷新；首次请求会实时采集。
    """
    await _refresh_cache(force=False)
    if _snapshot_cache["data"] is None:
        raise HTTPException(status_code=503, detail="Snapshot not ready, please retry in a moment")
    return _snapshot_cache["data"]


@api_router.post("/system/snapshot/refresh")
async def force_refresh_snapshot(
    current_user: User = Depends(get_current_active_user)
):
    """强制刷新快照缓存（忽略 TTL）"""
    await _refresh_cache(force=True)
    return {"message": "Snapshot refreshed", "updated_at": _snapshot_cache["updated_at"]}


@api_router.get("/system/stream")
async def stream_snapshot(
    current_user: User = Depends(get_current_active_user)
):
    """
    SSE 端点：订阅实时快照推送。
    每次缓存刷新时，所有订阅客户端会收到最新快照。
    前端用 EventSource 订阅此端点即可实现近实时更新。
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    _SSE_CLIENTS.append(queue)

    # 立即推送当前缓存（如果有）
    if _snapshot_cache["data"]:
        await queue.put(f"data: {json.dumps(_snapshot_cache['data'], ensure_ascii=False)}\n\n")

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25)
                    yield event
                except asyncio.TimeoutError:
                    # 每 25 秒发送一次 keep-alive
                    yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                _SSE_CLIENTS.remove(queue)
            except ValueError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# 保持向后兼容的端点
@api_router.get("/staff")
async def get_staff_snapshot(
    current_user: User = Depends(get_current_active_user)
):
    """获取Staff视图（简化版）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from staff_monitor import StaffMonitor

    monitor = StaffMonitor()
    snapshot = monitor.get_staff_snapshot()

    return {
        "generated_at": snapshot.generated_at,
        "summary": {
            "total_agents": snapshot.total_agents,
            "truly_active": snapshot.truly_active,
            "only_queued": snapshot.only_queued,
            "idle": snapshot.idle,
            "blocked": snapshot.blocked
        },
        "entries": [{
            "agent_id": e.agent_id,
            "display_name": e.display_name,
            "status": e.status.value,
            "is_truly_active": e.is_truly_active,
            "current_task": e.current_task,
            "queue_depth": e.queue_depth,
            "last_output": e.last_output,
            "last_active_at": e.last_active_at,
            "session_count": e.session_count,
            "estimated_tokens": e.estimated_tokens
        } for e in snapshot.entries]
    }


# ============== Staff Routes (Phase 1 Integration) ==============

@api_router.get("/staff/exceptions")
async def get_staff_exceptions(
    current_user: User = Depends(get_current_active_user)
):
    """获取Staff异常摘要（阻塞、错误、等待审批）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from staff_monitor import StaffMonitor

    monitor = StaffMonitor()
    exceptions = monitor.get_exceptions_summary()

    return exceptions


# ============== Context Pressure Routes (Phase 2 Integration) ==============

@api_router.get("/context-pressure")
async def get_context_pressure(
    current_user: User = Depends(get_current_active_user)
):
    """获取上下文压力监控（从Control Center提取）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from context_monitor import ContextPressureMonitor

    monitor = ContextPressureMonitor()
    snapshot = monitor.get_all_sessions_pressure()

    return {
        "generated_at": snapshot.generated_at,
        "summary": {
            "total_sessions": snapshot.total_sessions,
            "ok": snapshot.ok_count,
            "warn": snapshot.warn_count,
            "critical": snapshot.critical_count
        },
        "entries": [{
            "session_id": e.session_id,
            "agent_id": e.agent_id,
            "current_tokens": e.current_tokens,
            "usage_percent": e.usage_percent,
            "pressure_level": e.pressure_level.value,
            "estimated_cost": e.estimated_cost,
            "recommendation": e.recommendation
        } for e in snapshot.entries]
    }


@api_router.get("/context-pressure/summary")
async def get_context_pressure_summary(
    current_user: User = Depends(get_current_active_user)
):
    """获取上下文压力摘要"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from context_monitor import ContextPressureMonitor

    monitor = ContextPressureMonitor()
    summary = monitor.get_pressure_summary()

    return summary


# ============== System Status API (新增) ==============

@api_router.get("/system/status")
async def get_system_status(
    current_user: User = Depends(get_current_active_user)
):
    """获取系统运行状态（Overseer + Architect可视化）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    try:
        from system_visualizer import SystemOperationVisualizer

        visualizer = SystemOperationVisualizer()
        status = visualizer.get_full_system_status()

        return status
    except Exception as e:
        # 如果可视化器失败，返回基本状态
        return {
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "overseer": {
                "agent_name": "Overseer (监控优化师)",
                "status": "running",
                "capabilities": ["自动采集", "效能评分", "异常识别"],
                "health": "healthy"
            },
            "architect": {
                "agent_name": "Architect (进化导师)",
                "status": "running",
                "capabilities": ["缺口识别", "提案生成", "自动部署"],
                "proposals": {"total": 10, "pending": 0, "approved": 1, "applied": 1},
                "health": "healthy"
            },
            "error": str(e)
        }


# ============== Proposal Management API (完整功能) ==============

@api_router.get("/proposals/all")
async def get_all_proposals_detail(
    current_user: User = Depends(get_current_active_user)
):
    """获取所有提案详情（完整列表）"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from proposal_manager import get_proposal_manager

    manager = get_proposal_manager()
    proposals = manager.get_all_proposals()
    stats = manager.get_statistics()

    return {
        "statistics": stats,
        "proposals": proposals
    }


@api_router.get("/proposals/{proposal_id}")
async def get_proposal_detail_api(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取单个提案详情"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from proposal_manager import get_proposal_manager

    manager = get_proposal_manager()
    proposal = manager.get_proposal_detail(proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return proposal


@api_router.post("/proposals/{proposal_id}/approve")
async def approve_proposal_api(
    proposal_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """批准提案"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from proposal_manager import get_proposal_manager

    manager = get_proposal_manager()
    success = manager.approve_proposal(proposal_id)

    if not success:
        raise HTTPException(status_code=400, detail="Proposal already processed")

    return {"message": "Proposal approved", "proposal_id": proposal_id}


@api_router.post("/proposals/{proposal_id}/reject")
async def reject_proposal_api(
    proposal_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_active_user)
):
    """拒绝提案"""
    import sys
    sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')

    from proposal_manager import get_proposal_manager

    manager = get_proposal_manager()
    success = manager.reject_proposal(proposal_id, reason)

    if not success:
        raise HTTPException(status_code=400, detail="Proposal already processed")

    return {"message": "Proposal rejected", "proposal_id": proposal_id}
