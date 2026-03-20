#!/usr/bin/env python3
"""
Full Data Collector - 完整数据采集器
基于 OpenClaw Control Center 的完整数据模型
采集：sessions, approvals, budget, tasks, projects 全部数据
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib


class AgentRunState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"


class AlertLevel(str, Enum):
    INFO = "info"
    WARN = "warn"
    ACTION_REQUIRED = "action-required"


@dataclass
class SessionDetail:
    """完整的Session详情"""
    session_key: str
    label: Optional[str]
    agent_id: str
    state: AgentRunState
    last_message_at: Optional[str]
    model: Optional[str]
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    message_count: int = 0
    tool_calls: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    waiting_approvals: List[str] = field(default_factory=list)
    first_message_at: Optional[str] = None
    duration_minutes: float = 0.0


@dataclass
class ApprovalDetail:
    """审批详情"""
    approval_id: str
    session_key: Optional[str]
    agent_id: Optional[str]
    status: str  # pending | approved | denied
    command: Optional[str]
    reason: Optional[str]
    requested_at: Optional[str]
    updated_at: Optional[str]


@dataclass
class BudgetMetric:
    """预算指标"""
    scope: str  # agent | project | task
    scope_id: str
    label: str
    used: int
    limit: int
    warn_at: int
    usage_percent: float
    status: str  # ok | warn | over
    estimated_cost: float


@dataclass
class TaskDetail:
    """任务详情"""
    task_id: str
    project_id: str
    project_title: str
    title: str
    status: str  # todo | in_progress | blocked | done
    owner: str
    due_at: Optional[str]
    session_keys: List[str]
    artifacts_count: int
    updated_at: str


@dataclass
class ProjectDetail:
    """项目详情"""
    project_id: str
    title: str
    status: str
    owner: str
    total_tasks: int
    todo: int
    in_progress: int
    blocked: int
    done: int
    due: int
    updated_at: str


@dataclass
class AlertItem:
    """告警项"""
    level: AlertLevel
    code: str
    message: str
    route: str
    source: str
    count: int


@dataclass
class FullSystemSnapshot:
    """完整系统快照"""
    generated_at: str

    # Sessions
    sessions: List[SessionDetail]
    session_count: int
    active_sessions: int
    blocked_sessions: int
    error_sessions: int

    # Approvals
    approvals: List[ApprovalDetail]
    pending_approvals: int
    approved_count: int
    denied_count: int

    # Budget
    budget_metrics: List[BudgetMetric]
    total_budget_scopes: int
    over_budget_count: int
    warn_budget_count: int
    total_estimated_cost: float

    # Tasks
    tasks: List[TaskDetail]
    total_tasks: int
    todo_count: int
    in_progress_count: int
    blocked_count: int
    done_count: int
    due_soon_count: int

    # Projects
    projects: List[ProjectDetail]
    total_projects: int

    # Alerts
    alerts: List[AlertItem]
    info_alerts: int
    warn_alerts: int
    action_required_alerts: int


class FullDataCollector:
    """完整数据采集器"""

    def __init__(self):
        self.openclaw_home = Path.home() / ".openclaw"
        self.agents_dir = self.openclaw_home / "agents"
        self.workspace_dir = Path.home() / ".openclaw" / "workspace"

    def parse_session_file(self, jsonl_path: Path, agent_id: str) -> Optional[SessionDetail]:
        """完整解析单个session文件"""

        messages = []
        errors = []
        waiting_approvals = []
        tool_calls = []

        first_time = None
        last_time = None
        model = None
        label = None

        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        record = json.loads(line)

                        # 获取session基本信息
                        if record.get('type') == 'session':
                            label = record.get('label')
                            if not first_time:
                                first_time = record.get('timestamp')

                        # 获取模型
                        if record.get('type') == 'model_change':
                            model = record.get('modelId', model)

                        # 统计消息
                        if record.get('type') == 'message':
                            messages.append(record)
                            ts = record.get('timestamp')
                            if ts:
                                if not first_time:
                                    first_time = ts
                                last_time = ts

                        # 统计tool调用（真实格式：嵌在 message.content[] 里 type=tool_use）
                        if record.get('type') == 'tool_call':
                            tool_name = record.get('tool') or record.get('name')
                            if tool_name:
                                tool_calls.append(tool_name)

                        # OpenClaw 真实格式：工具调用藏在 message.content 的 toolCall item 里
                        # 实际字段名是 "toolCall"（驼峰），不是 "tool_use"
                        if record.get('type') == 'message':
                            msg_obj = record.get('message', {})
                            content = msg_obj.get('content', [])
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        # 同时兼容 toolCall / tool_use / tool_call 三种写法
                                        if item.get('type') in ('toolCall', 'tool_use', 'tool_call'):
                                            tool_name = item.get('name', '')
                                            if tool_name:
                                                tool_calls.append(tool_name)

                        # 检测错误
                        if record.get('type') == 'error' or record.get('error'):
                            error_msg = str(record.get('error', 'Unknown error'))[:200]
                            errors.append(error_msg)

                        # 检测等待审批
                        content = str(record)
                        if any(kw in content.lower() for kw in ['approval', '等待审批', '确认', 'approve']):
                            waiting_approvals.append("pending approval detected")

                        # 检测阻塞
                        if any(kw in content.lower() for kw in ['blocked', '阻塞', 'waiting']):
                            if 'waiting_approval' not in [e[:20] for e in errors]:
                                pass  # 将在状态判断中处理

                    except json.JSONDecodeError:
                        continue

            if not messages:
                return None

            # 计算统计数据
            total_chars_in = 0
            total_chars_out = 0

            for msg in messages:
                message = msg.get('message', {})
                content = message.get('content', [])
                role = message.get('role', '')

                text_len = 0
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text_len += len(item.get('text', ''))
                elif isinstance(content, str):
                    text_len = len(content)

                if role == 'user':
                    total_chars_in += text_len
                else:
                    total_chars_out += text_len

            # Token估算 (更精确：中文1.5字符/token，英文4字符/token)
            tokens_in = total_chars_in // 2  # 混合估算
            tokens_out = total_chars_out // 2

            # 成本估算 ($0.002 per 1K tokens for input, $0.006 for output)
            cost = (tokens_in / 1000 * 0.002) + (tokens_out / 1000 * 0.006)

            # 计算持续时间
            duration = 0
            if first_time and last_time:
                try:
                    t1 = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                    t2 = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    duration = (t2 - t1).total_seconds() / 60
                except:
                    pass

            # 判断状态
            now = datetime.now()
            state = AgentRunState.IDLE

            if last_time:
                try:
                    last_dt = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                    if (now - last_dt) < timedelta(minutes=5):
                        if errors:
                            state = AgentRunState.ERROR
                        elif waiting_approvals:
                            state = AgentRunState.WAITING_APPROVAL
                        else:
                            state = AgentRunState.RUNNING
                    elif (now - last_dt) < timedelta(hours=1):
                        if errors:
                            state = AgentRunState.ERROR
                        elif waiting_approvals:
                            state = AgentRunState.WAITING_APPROVAL
                        else:
                            state = AgentRunState.BLOCKED
                    else:
                        state = AgentRunState.IDLE
                except:
                    state = AgentRunState.IDLE

            if errors and state == AgentRunState.IDLE:
                state = AgentRunState.ERROR

            return SessionDetail(
                session_key=jsonl_path.stem,
                label=label,
                agent_id=agent_id,
                state=state,
                last_message_at=last_time,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=round(cost, 4),
                message_count=len(messages),
                tool_calls=list(set(tool_calls)),
                errors=errors[:5],  # 最多5个错误
                waiting_approvals=waiting_approvals[:3],
                first_message_at=first_time,
                duration_minutes=round(duration, 1)
            )

        except Exception as e:
            print(f"⚠️ 解析失败 {jsonl_path}: {e}")
            return None

    def collect_all_sessions(self, hours: int = 24) -> List[SessionDetail]:
        """采集所有session的完整数据"""
        sessions = []
        cutoff = datetime.now() - timedelta(hours=hours)

        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue

            for jsonl_file in sessions_dir.glob("*.jsonl"):
                if ".deleted." in jsonl_file.name or ".reset." in jsonl_file.name:
                    continue

                try:
                    mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                    if mtime < cutoff:
                        continue

                    session = self.parse_session_file(jsonl_file, agent_dir.name)
                    if session:
                        sessions.append(session)

                except Exception as e:
                    continue

        return sorted(sessions, key=lambda s: s.last_message_at or '', reverse=True)

    def detect_approvals(self, sessions: List[SessionDetail]) -> List[ApprovalDetail]:
        """从session中检测审批请求"""
        approvals = []

        for session in sessions:
            if session.waiting_approvals:
                approval = ApprovalDetail(
                    approval_id=f"approval_{session.session_key[:8]}",
                    session_key=session.session_key,
                    agent_id=session.agent_id,
                    status="pending",
                    command=session.waiting_approvals[0] if session.waiting_approvals else None,
                    reason="Waiting for user approval",
                    requested_at=session.last_message_at,
                    updated_at=session.last_message_at
                )
                approvals.append(approval)

        return approvals

    def _load_budget_config(self) -> dict:
        """加载预算配置文件，不存在时返回默认配置"""
        config_path = self.workspace_dir / "metrics" / "budget_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 预算配置加载失败: {e}，使用默认值")
        return {
            "global_default_limit": 100000,
            "dynamic_adjustment": {"enabled": False},
            "agent_overrides": {}
        }

    def _calc_efficiency(self, sessions_for_agent: List[SessionDetail]) -> dict:
        """计算单个 Agent 的效能指标（用于动态预算调整）"""
        calls = len(sessions_for_agent)
        if calls == 0:
            return {"efficiency_score": 0.0, "success_rate": 0.0, "grade": "C"}

        success = sum(1 for s in sessions_for_agent if not s.errors)
        total_tokens = sum(s.tokens_in + s.tokens_out for s in sessions_for_agent)
        success_rate = success / calls
        token_k = max(total_tokens / 1000, 0.1)
        efficiency_score = round((calls * success_rate) / token_k, 2)

        if efficiency_score > 10 and success_rate > 0.9:
            grade = "A"
        elif efficiency_score >= 5 and success_rate >= 0.7:
            grade = "B"
        else:
            grade = "C"

        return {
            "efficiency_score": efficiency_score,
            "success_rate": success_rate,
            "grade": grade
        }

    def _calc_dynamic_limit(self, agent_id: str, base_limit: int,
                            perf: dict, cfg: dict) -> tuple:
        """根据效能计算动态配额上限，返回 (limit, note)"""
        dyn = cfg.get("dynamic_adjustment", {})
        if not dyn.get("enabled", False):
            return base_limit, "static"

        grade = perf.get("grade", "C")
        eff   = perf.get("efficiency_score", 0)
        sr    = perf.get("success_rate", 0)

        factor = 1.0
        note   = "dynamic:C→keep"

        for rule in dyn.get("rules", []):
            if rule.get("grade") == grade:
                factor = rule.get("factor", 1.0)
                note   = f"dynamic:{grade}×{factor}"
                break

        new_limit = int(base_limit * factor)
        max_l = dyn.get("max_limit", 1_000_000)
        min_l = dyn.get("min_limit", 50_000)
        new_limit = max(min_l, min(max_l, new_limit))
        return new_limit, note

    def calculate_budget(self, sessions: List[SessionDetail]) -> List[BudgetMetric]:
        """计算预算指标（支持动态配额 + 手动覆盖）"""
        cfg = self._load_budget_config()
        global_default = cfg.get("global_default_limit", 100000)
        overrides = cfg.get("agent_overrides", {})

        # 按 Agent 聚合 usage
        agent_usage: dict = {}
        agent_sessions: dict = {}
        for session in sessions:
            aid = session.agent_id
            if aid not in agent_usage:
                agent_usage[aid]   = {'tokens': 0, 'cost': 0.0}
                agent_sessions[aid] = []
            agent_usage[aid]['tokens'] += session.tokens_in + session.tokens_out
            agent_usage[aid]['cost']   += session.cost
            agent_sessions[aid].append(session)

        metrics = []
        for agent_id, usage in agent_usage.items():
            used = usage['tokens']
            ov   = overrides.get(agent_id, {})

            # 1. 手动覆盖优先
            if ov.get("manual_override", False):
                limit = ov.get("limit", global_default)
                limit_note = f"manual:{limit}"
            else:
                # 2. 动态调整
                base  = ov.get("limit", global_default)
                perf  = self._calc_efficiency(agent_sessions[agent_id])
                limit, limit_note = self._calc_dynamic_limit(agent_id, base, perf, cfg)

            warn_at       = int(limit * 0.8)
            usage_percent = (used / limit * 100) if limit > 0 else 0

            if used > limit:
                status = "over"
            elif used > warn_at:
                status = "warn"
            else:
                status = "ok"

            metrics.append(BudgetMetric(
                scope="agent",
                scope_id=agent_id,
                label=agent_id,
                used=used,
                limit=limit,
                warn_at=warn_at,
                usage_percent=round(usage_percent, 1),
                status=status,
                estimated_cost=round(usage['cost'], 4)
            ))

        return sorted(metrics, key=lambda m: m.usage_percent, reverse=True)

    def generate_alerts(self, snapshot: FullSystemSnapshot) -> List[AlertItem]:
        """生成告警"""
        alerts = []

        if snapshot.session_count == 0:
            alerts.append(AlertItem(
                level=AlertLevel.INFO,
                code="NO_SESSIONS",
                message="No active sessions detected",
                route="timeline",
                source="system",
                count=0
            ))

        if snapshot.blocked_sessions > 0:
            alerts.append(AlertItem(
                level=AlertLevel.WARN,
                code="HAS_BLOCKED",
                message=f"{snapshot.blocked_sessions} session(s) are blocked",
                route="operator-watch",
                source="session",
                count=snapshot.blocked_sessions
            ))

        if snapshot.error_sessions > 0:
            alerts.append(AlertItem(
                level=AlertLevel.ACTION_REQUIRED,
                code="HAS_ERRORS",
                message=f"{snapshot.error_sessions} session(s) are in error state",
                route="action-queue",
                source="session",
                count=snapshot.error_sessions
            ))

        if snapshot.pending_approvals > 0:
            alerts.append(AlertItem(
                level=AlertLevel.ACTION_REQUIRED,
                code="HAS_PENDING_APPROVALS",
                message=f"{snapshot.pending_approvals} approval request(s) pending",
                route="action-queue",
                source="approval",
                count=snapshot.pending_approvals
            ))

        if snapshot.over_budget_count > 0:
            alerts.append(AlertItem(
                level=AlertLevel.ACTION_REQUIRED,
                code="HAS_OVER_BUDGET",
                message=f"{snapshot.over_budget_count} budget scope(s) are over limit",
                route="action-queue",
                source="budget",
                count=snapshot.over_budget_count
            ))

        return alerts

    def get_full_snapshot(self) -> FullSystemSnapshot:
        """获取完整系统快照"""

        # 1. 采集所有session
        sessions = self.collect_all_sessions(hours=24)

        # 2. 检测审批
        approvals = self.detect_approvals(sessions)

        # 3. 计算预算
        budget_metrics = self.calculate_budget(sessions)

        # 4. 生成项目（从Agent推断）
        projects = []
        agent_ids = set(s.agent_id for s in sessions)
        for idx, agent_id in enumerate(agent_ids):
            agent_sessions = [s for s in sessions if s.agent_id == agent_id]
            projects.append(ProjectDetail(
                project_id=f"proj_{idx}",
                title=f"Project {agent_id}",
                status="active",
                owner=agent_id,
                total_tasks=len(agent_sessions),
                todo=sum(1 for s in agent_sessions if s.state == AgentRunState.IDLE),
                in_progress=sum(1 for s in agent_sessions if s.state == AgentRunState.RUNNING),
                blocked=sum(1 for s in agent_sessions if s.state == AgentRunState.BLOCKED),
                done=sum(1 for s in agent_sessions if s.state == AgentRunState.IDLE and not s.errors),
                due=0,
                updated_at=datetime.now().isoformat()
            ))

        # 5. 生成任务（从session推断）
        tasks = []
        for idx, session in enumerate(sessions[:20]):  # 最多20个
            tasks.append(TaskDetail(
                task_id=f"task_{session.session_key[:8]}",
                project_id=next((p.project_id for p in projects if p.owner == session.agent_id), "unknown"),
                project_title=session.agent_id,
                title=session.label or f"Task from {session.session_key[:8]}",
                status=session.state.value,
                owner=session.agent_id,
                due_at=None,
                session_keys=[session.session_key],
                artifacts_count=len(session.tool_calls),
                updated_at=session.last_message_at or datetime.now().isoformat()
            ))

        # 6. 创建快照
        snapshot = FullSystemSnapshot(
            generated_at=datetime.now().isoformat(),
            sessions=sessions,
            session_count=len(sessions),
            active_sessions=sum(1 for s in sessions if s.state == AgentRunState.RUNNING),
            blocked_sessions=sum(1 for s in sessions if s.state == AgentRunState.BLOCKED),
            error_sessions=sum(1 for s in sessions if s.state == AgentRunState.ERROR),
            approvals=approvals,
            pending_approvals=sum(1 for a in approvals if a.status == "pending"),
            approved_count=sum(1 for a in approvals if a.status == "approved"),
            denied_count=sum(1 for a in approvals if a.status == "denied"),
            budget_metrics=budget_metrics,
            total_budget_scopes=len(budget_metrics),
            over_budget_count=sum(1 for b in budget_metrics if b.status == "over"),
            warn_budget_count=sum(1 for b in budget_metrics if b.status == "warn"),
            total_estimated_cost=sum(b.estimated_cost for b in budget_metrics),
            tasks=tasks,
            total_tasks=len(tasks),
            todo_count=sum(1 for t in tasks if t.status == "todo"),
            in_progress_count=sum(1 for t in tasks if t.status == "in_progress"),
            blocked_count=sum(1 for t in tasks if t.status == "blocked"),
            done_count=sum(1 for t in tasks if t.status == "done"),
            due_soon_count=0,
            projects=projects,
            total_projects=len(projects),
            alerts=[],
            info_alerts=0,
            warn_alerts=0,
            action_required_alerts=0
        )

        # 7. 生成告警
        snapshot.alerts = self.generate_alerts(snapshot)
        snapshot.info_alerts = sum(1 for a in snapshot.alerts if a.level == AlertLevel.INFO)
        snapshot.warn_alerts = sum(1 for a in snapshot.alerts if a.level == AlertLevel.WARN)
        snapshot.action_required_alerts = sum(1 for a in snapshot.alerts if a.level == AlertLevel.ACTION_REQUIRED)

        return snapshot


# 测试
if __name__ == "__main__":
    print("🎯 Full Data Collector 测试")
    print("="*60)

    collector = FullDataCollector()
    snapshot = collector.get_full_snapshot()

    print(f"\n📊 完整系统快照 ({snapshot.generated_at})")
    print("="*60)

    print(f"\n📋 Sessions ({snapshot.session_count}):")
    print(f"  活跃: {snapshot.active_sessions}, 阻塞: {snapshot.blocked_sessions}, 错误: {snapshot.error_sessions}")
    for s in snapshot.sessions[:3]:
        print(f"  • {s.session_key[:20]}... [{s.state.value}] {s.tokens_in+s.tokens_out} tokens, ${s.cost}")

    print(f"\n✅ Approvals ({snapshot.pending_approvals} pending):")
    for a in snapshot.approvals[:3]:
        print(f"  • {a.approval_id}: {a.status}")

    print(f"\n💰 Budget ({snapshot.total_budget_scopes} scopes):")
    print(f"  总成本: ${snapshot.total_estimated_cost:.4f}")
    print(f"  超限: {snapshot.over_budget_count}, 警告: {snapshot.warn_budget_count}")
    for b in snapshot.budget_metrics[:3]:
        print(f"  • {b.scope_id}: {b.usage_percent}% (${b.estimated_cost})")

    print(f"\n📁 Projects ({snapshot.total_projects}):")
    for p in snapshot.projects[:3]:
        print(f"  • {p.title}: {p.in_progress}进行中, {p.blocked}阻塞")

    print(f"\n⚠️  Alerts ({len(snapshot.alerts)}):")
    for a in snapshot.alerts:
        emoji = "🔴" if a.level == AlertLevel.ACTION_REQUIRED else "🟡" if a.level == AlertLevel.WARN else "🔵"
        print(f"  {emoji} [{a.level.value}] {a.code}: {a.message}")

    print("\n✅ 完整数据采集成功！")
