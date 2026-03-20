#!/usr/bin/env python3
"""
Collaboration Tracker - Agent协作追踪器
提取自 OpenClaw Control Center 的 commander.ts
功能: 父子session交接、跨session消息追踪
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class HandoffEvent:
    """交接事件"""
    event_id: str
    from_session: str
    to_session: str
    from_agent: str
    to_agent: str
    task: str
    status: str  # pending | in_progress | completed
    timestamp: str
    handoff_type: str  # handoff | message | relay


class CollaborationTracker:
    """协作追踪器"""
    
    def __init__(self):
        self.openclaw_home = Path.home() / ".openclaw"
        self.agents_dir = self.openclaw_home / "agents"
    
    def trace_collaboration(self, hours: int = 24) -> List[Dict]:
        """追踪Agent间协作"""
        events = []
        
        # 扫描session文件中的协作信号
        # 1. sessions_send 调用
        # 2. parent-child session关系
        # 3. 任务交接模式
        
        for agent_dir in self.agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            sessions_dir = agent_dir / "sessions"
            if not sessions_dir.exists():
                continue
            
            for jsonl_file in sessions_dir.glob("*.jsonl"):
                try:
                    with open(jsonl_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            
                            try:
                                record = json.loads(line)
                                
                                # 检测协作信号
                                # 类型1: 显式的session引用
                                content = str(record)
                                
                                # 查找sessions_send模式
                                if "sessions_send" in content:
                                    events.append({
                                        "type": "message",
                                        "from_agent": agent_dir.name,
                                        "timestamp": record.get('timestamp', ''),
                                        "pattern": "sessions_send",
                                        "details": "跨session消息发送"
                                    })
                                
                                # 查找parent session关系
                                if "parent" in content.lower() or "child" in content.lower():
                                    events.append({
                                        "type": "relay",
                                        "from_agent": agent_dir.name,
                                        "timestamp": record.get('timestamp', ''),
                                        "pattern": "parent-child",
                                        "details": "父子session交接"
                                    })
                                
                                # 查找spawn/subagent模式
                                if any(kw in content.lower() for kw in ["spawn", "subagent", "delegate"]):
                                    events.append({
                                        "type": "handoff",
                                        "from_agent": agent_dir.name,
                                        "timestamp": record.get('timestamp', ''),
                                        "pattern": "spawn",
                                        "details": "任务委托给子Agent"
                                    })
                                
                            except:
                                continue
                                
                except Exception as e:
                    continue
        
        return sorted(events, key=lambda x: x.get('timestamp', ''), reverse=True)[:20]


if __name__ == "__main__":
    tracker = CollaborationTracker()
    events = tracker.trace_collaboration()
    print(f"发现 {len(events)} 个协作事件")
    for e in events[:5]:
        print(f"  {e['type']}: {e['from_agent']} - {e['details']}")
