#!/usr/bin/env python3
"""
Staff Monitor - Agent工作状态监控器
提取自 OpenClaw Control Center 的 agent-roster.ts + commander.ts
功能: 区分真正工作的Agent vs 仅排队的Agent
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
from enum import Enum


class AgentRunState(str, Enum):
    """Agent运行状态"""
    IDLE = "idle"                    # 空闲
    RUNNING = "running"              # 真正执行中
    BLOCKED = "blocked"              # 被阻塞
    WAITING_APPROVAL = "waiting_approval"  # 等待审批
    ERROR = "error"                  # 错误状态
    QUEUED = "queued"                # 仅排队，未真正执行


@dataclass
class StaffEntry:
    """Agent工作人员条目"""
    agent_id: str                    # Agent ID
    display_name: str                # 显示名称
    status: AgentRunState            # 当前状态
    is_truly_active: bool            # 是否真正活跃（vs仅排队）
    current_task: Optional[str]      # 当前任务
    queue_depth: int                 # 队列深度
    last_output: Optional[str]       # 最后输出
    last_active_at: Optional[str]    # 最后活跃时间
    session_count: int               # 会话数量
    estimated_tokens: int            # 预估Token消耗


@dataclass
class StaffSnapshot:
    """Staff视图快照"""
    generated_at: str
    total_agents: int
    truly_active: int                # 真正活跃的
    only_queued: int                 # 仅排队的
    idle: int                        # 空闲的
    blocked: int                     # 被阻塞的
    entries: List[StaffEntry]


class StaffMonitor:
    """Agent工作状态监控器"""
    
    def __init__(self):
        self.openclaw_home = Path.home() / ".openclaw"
        self.agents_dir = self.openclaw_home / "agents"
        self.workspace_dir = Path.home() / ".openclaw" / "workspace"
        
    def get_agent_roster(self) -> List[Dict]:
        """获取Agent名单（从runtime目录）"""
        roster = []
        
        if not self.agents_dir.exists():
            return roster
        
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            # 检查是否有sessions目录
            sessions_dir = agent_dir / "sessions"
            has_activity = sessions_dir.exists() and any(sessions_dir.glob("*.jsonl"))
            
            roster.append({
                "agent_id": agent_dir.name,
                "display_name": agent_dir.name,
                "has_activity": has_activity,
                "path": str(agent_dir)
            })
        
        return sorted(roster, key=lambda x: x["agent_id"])
    
    def analyze_agent_activity(self, agent_id: str) -> StaffEntry:
        """分析特定Agent的活动状态"""
        sessions_dir = self.agents_dir / agent_id / "sessions"
        
        if not sessions_dir.exists():
            return StaffEntry(
                agent_id=agent_id,
                display_name=agent_id,
                status=AgentRunState.IDLE,
                is_truly_active=False,
                current_task=None,
                queue_depth=0,
                last_output=None,
                last_active_at=None,
                session_count=0,
                estimated_tokens=0
            )
        
        # 读取最近24小时的会话
        recent_sessions = []
        cutoff = datetime.now() - timedelta(hours=24)
        
        for jsonl_file in sessions_dir.glob("*.jsonl"):
            if ".deleted." in jsonl_file.name or ".reset." in jsonl_file.name:
                continue
            
            try:
                mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                if mtime < cutoff:
                    continue
                
                # 解析文件内容
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            record['_source_file'] = jsonl_file.name
                            record['_mtime'] = mtime.isoformat()
                            recent_sessions.append(record)
                        except:
                            continue
            except Exception as e:
                print(f"⚠️ 读取失败 {jsonl_file}: {e}")
        
        # 分析会话状态
        return self._determine_status(agent_id, recent_sessions)
    
    def _determine_status(self, agent_id: str, sessions: List[Dict]) -> StaffEntry:
        """根据会话数据确定Agent状态"""
        
        if not sessions:
            return StaffEntry(
                agent_id=agent_id,
                display_name=agent_id,
                status=AgentRunState.IDLE,
                is_truly_active=False,
                current_task=None,
                queue_depth=0,
                last_output=None,
                last_active_at=None,
                session_count=0,
                estimated_tokens=0
            )
        
        # 统计消息数量
        message_count = 0
        last_message_time = None
        last_content = None
        total_tokens = 0
        
        # 检查是否有阻塞/错误
        has_error = False
        has_waiting = False
        
        for session in sessions:
            # 消息统计
            if session.get('type') == 'message':
                message_count += 1
                
                # 时间
                ts = session.get('timestamp') or session.get('_mtime')
                if ts:
                    try:
                        msg_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        if not last_message_time or msg_time > last_message_time:
                            last_message_time = msg_time
                            message = session.get('message', {})
                            content = message.get('content', [])
                            if isinstance(content, list) and content:
                                last_content = content[0].get('text', '')[:100]
                            elif isinstance(content, str):
                                last_content = content[:100]
                    except:
                        pass
                
                # Token估算
                message = session.get('message', {})
                content = message.get('content', [])
                text_len = 0
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text_len += len(item.get('text', ''))
                elif isinstance(content, str):
                    text_len = len(content)
                total_tokens += text_len // 4
            
            # 错误检测
            if session.get('type') == 'error' or session.get('error'):
                has_error = True
            
            # 等待审批检测
            if 'approval' in str(session).lower() or 'waiting' in str(session).lower():
                has_waiting = True
        
        # 确定状态
        # 如果在最近5分钟有活动 → RUNNING
        # 如果有错误 → ERROR
        # 如果等待审批 → WAITING_APPROVAL
        # 否则根据queue深度判断是QUEUED还是IDLE
        
        now = datetime.now()
        if last_message_time and (now - last_message_time) < timedelta(minutes=5):
            status = AgentRunState.RUNNING
            is_active = True
            current_task = last_content or "处理中..."
        elif has_error:
            status = AgentRunState.ERROR
            is_active = False
            current_task = "发生错误"
        elif has_waiting:
            status = AgentRunState.WAITING_APPROVAL
            is_active = False
            current_task = "等待审批"
        elif message_count > 0:
            # 有历史记录但最近不活跃
            if last_message_time and (now - last_message_time) < timedelta(hours=1):
                status = AgentRunState.QUEUED
                is_active = False
                current_task = "排队等待"
            else:
                status = AgentRunState.IDLE
                is_active = False
                current_task = None
        else:
            status = AgentRunState.IDLE
            is_active = False
            current_task = None
        
        return StaffEntry(
            agent_id=agent_id,
            display_name=agent_id,
            status=status,
            is_truly_active=is_active,
            current_task=current_task,
            queue_depth=message_count // 10,  # 粗略估算
            last_output=last_content,
            last_active_at=last_message_time.isoformat() if last_message_time else None,
            session_count=len(set(s.get('_source_file') for s in sessions)),
            estimated_tokens=total_tokens
        )
    
    def get_staff_snapshot(self) -> StaffSnapshot:
        """获取完整的Staff视图快照"""
        
        roster = self.get_agent_roster()
        entries = []
        
        for agent_info in roster:
            entry = self.analyze_agent_activity(agent_info["agent_id"])
            entries.append(entry)
        
        # 统计
        truly_active = sum(1 for e in entries if e.is_truly_active)
        only_queued = sum(1 for e in entries if e.status == AgentRunState.QUEUED)
        idle = sum(1 for e in entries if e.status == AgentRunState.IDLE)
        blocked = sum(1 for e in entries if e.status in [AgentRunState.BLOCKED, AgentRunState.ERROR])
        
        return StaffSnapshot(
            generated_at=datetime.now().isoformat(),
            total_agents=len(entries),
            truly_active=truly_active,
            only_queued=only_queued,
            idle=idle,
            blocked=blocked,
            entries=entries
        )
    
    def get_exceptions_summary(self) -> Dict:
        """获取异常摘要（被阻塞、错误、等待审批）"""
        snapshot = self.get_staff_snapshot()
        
        blocked = []
        errors = []
        waiting_approval = []
        
        for entry in snapshot.entries:
            if entry.status == AgentRunState.BLOCKED:
                blocked.append({
                    "agent_id": entry.agent_id,
                    "reason": entry.current_task or "未知原因"
                })
            elif entry.status == AgentRunState.ERROR:
                errors.append({
                    "agent_id": entry.agent_id,
                    "reason": entry.current_task or "执行错误"
                })
            elif entry.status == AgentRunState.WAITING_APPROVAL:
                waiting_approval.append({
                    "agent_id": entry.agent_id,
                    "reason": entry.current_task or "等待审批"
                })
        
        return {
            "generated_at": snapshot.generated_at,
            "blocked": blocked,
            "errors": errors,
            "pending_approvals": waiting_approval,
            "counts": {
                "blocked": len(blocked),
                "errors": len(errors),
                "pending_approvals": len(waiting_approval)
            }
        }


# 测试代码
if __name__ == "__main__":
    print("🎯 Staff Monitor 测试")
    print("="*60)
    
    monitor = StaffMonitor()
    
    # 获取Agent名单
    roster = monitor.get_agent_roster()
    print(f"\n📋 发现 {len(roster)} 个Agent:")
    for agent in roster:
        print(f"  • {agent['agent_id']}")
    
    # 获取Staff快照
    print("\n🔍 分析Agent活动状态...")
    snapshot = monitor.get_staff_snapshot()
    
    print(f"\n📊 Staff 视图快照 ({snapshot.generated_at}):")
    print(f"  总Agent数: {snapshot.total_agents}")
    print(f"  真正活跃: {snapshot.truly_active}")
    print(f"  仅排队: {snapshot.only_queued}")
    print(f"  空闲: {snapshot.idle}")
    print(f"  被阻塞: {snapshot.blocked}")
    
    print(f"\n👥 详细信息:")
    for entry in sorted(snapshot.entries, key=lambda x: x.is_truly_active, reverse=True):
        status_emoji = {
            AgentRunState.RUNNING: "🟢",
            AgentRunState.IDLE: "⚫",
            AgentRunState.QUEUED: "🟡",
            AgentRunState.BLOCKED: "🔴",
            AgentRunState.ERROR: "❌",
            AgentRunState.WAITING_APPROVAL: "⏸️"
        }.get(entry.status, "⚪")
        
        active_marker = "⚡" if entry.is_truly_active else "  "
        
        print(f"\n  {active_marker} {status_emoji} {entry.agent_id}")
        print(f"      状态: {entry.status.value}")
        print(f"      任务: {entry.current_task or '无'}")
        print(f"      会话数: {entry.session_count}, Tokens: {entry.estimated_tokens}")
        if entry.last_active_at:
            print(f"      最后活跃: {entry.last_active_at[:19]}")
    
    # 异常摘要
    print("\n" + "="*60)
    exceptions = monitor.get_exceptions_summary()
    if exceptions['counts']['blocked'] > 0 or exceptions['counts']['errors'] > 0:
        print("⚠️  异常摘要:")
        if exceptions['blocked']:
            print(f"  被阻塞: {len(exceptions['blocked'])}")
        if exceptions['errors']:
            print(f"  错误: {len(exceptions['errors'])}")
        if exceptions['pending_approvals']:
            print(f"  等待审批: {len(exceptions['pending_approvals'])}")
    else:
        print("✅ 无异常，系统运行正常")
