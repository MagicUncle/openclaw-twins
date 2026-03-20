#!/usr/bin/env python3
"""
Context Pressure Monitor - 上下文压力监控器
提取自 OpenClaw Control Center 的 commander.ts (token统计部分)
功能: 监控哪些session接近上下文限制，预测性能下降和成本增加
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass
from enum import Enum


class PressureLevel(str, Enum):
    """压力等级"""
    OK = "ok"           # 正常
    WARN = "warn"       # 警告（接近限制）
    CRITICAL = "critical"  # 严重（即将溢出）


@dataclass
class ContextPressureEntry:
    """上下文压力条目"""
    session_id: str                  # 会话ID
    agent_id: str                    # 所属Agent
    current_tokens: int              # 当前Token数
    threshold: int                   # 警告阈值
    max_context: int                 # 最大上下文限制
    pressure_level: PressureLevel    # 压力等级
    usage_percent: float             # 使用百分比
    estimated_cost: float            # 预估成本
    recommendation: Optional[str]    # 建议操作
    last_activity: Optional[str]     # 最后活动时间


@dataclass
class ContextPressureSnapshot:
    """上下文压力快照"""
    generated_at: str
    total_sessions: int
    ok_count: int
    warn_count: int
    critical_count: int
    entries: List[ContextPressureEntry]


class ContextPressureMonitor:
    """上下文压力监控器"""
    
    # 上下文限制配置（根据OpenClaw实际配置调整）
    CONTEXT_LIMITS = {
        "default": 8192,      # 默认8K上下文
        "claude-3-opus": 200000,  # Claude 3 Opus 200K
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "kimi-k2.5": 128000,
    }
    
    # 警告阈值（百分比）
    WARN_THRESHOLD = 0.75     # 75%警告
    CRITICAL_THRESHOLD = 0.90  # 90%严重
    
    def __init__(self):
        self.openclaw_home = Path.home() / ".openclaw"
        self.agents_dir = self.openclaw_home / "agents"
        
    def get_session_context_usage(self, session_file: Path) -> Optional[Dict]:
        """分析单个session文件的上下文使用情况"""
        
        try:
            total_tokens = 0
            message_count = 0
            last_activity = None
            agent_id = None
            model = "default"
            
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        record = json.loads(line)
                        
                        # 获取Agent ID
                        if not agent_id:
                            # 从文件路径推断
                            parts = session_file.parts
                            if 'agents' in parts:
                                idx = parts.index('agents')
                                if idx + 1 < len(parts):
                                    agent_id = parts[idx + 1]
                        
                        # 获取模型信息
                        if record.get('type') == 'model_change':
                            model = record.get('modelId', model)
                        
                        # 统计消息Token
                        if record.get('type') == 'message':
                            message = record.get('message', {})
                            content = message.get('content', [])
                            
                            # 计算token数（字符数/4作为粗略估算）
                            text_len = 0
                            if isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict):
                                        text_len += len(item.get('text', ''))
                            elif isinstance(content, str):
                                text_len = len(content)
                            
                            # 更精确的估算：英文约4字符/token，中文约1.5字符/token
                            # 简化处理：统一按3字符/token
                            estimated_tokens = text_len // 3
                            total_tokens += estimated_tokens
                            message_count += 1
                            
                            # 更新时间
                            ts = record.get('timestamp') or record.get('_mtime')
                            if ts:
                                last_activity = ts
                                
                    except json.JSONDecodeError:
                        continue
            
            if message_count == 0:
                return None
            
            # 获取上下文限制
            context_limit = self.CONTEXT_LIMITS.get(model, self.CONTEXT_LIMITS["default"])
            
            # 考虑系统开销（约20%）
            effective_limit = int(context_limit * 0.8)
            
            return {
                "session_id": session_file.stem,
                "agent_id": agent_id or "unknown",
                "model": model,
                "current_tokens": total_tokens,
                "message_count": message_count,
                "context_limit": context_limit,
                "effective_limit": effective_limit,
                "last_activity": last_activity
            }
            
        except Exception as e:
            print(f"⚠️ 分析session失败 {session_file}: {e}")
            return None
    
    def check_pressure(self, session_data: Dict) -> ContextPressureEntry:
        """检查单个session的压力状态"""
        
        current = session_data.get('current_tokens', 0)
        limit = session_data.get('effective_limit', 8192)
        max_limit = session_data.get('context_limit', 8192)
        
        # 计算使用百分比
        usage_percent = (current / limit) if limit > 0 else 0
        
        # 确定压力等级
        if usage_percent >= self.CRITICAL_THRESHOLD:
            level = PressureLevel.CRITICAL
            recommendation = "⚠️ 立即开启新session，当前session即将溢出"
        elif usage_percent >= self.WARN_THRESHOLD:
            level = PressureLevel.WARN
            recommendation = "建议开启新session，当前session接近限制"
        else:
            level = PressureLevel.OK
            recommendation = None
        
        # 预估成本（简化计算：$0.002 per 1K tokens）
        estimated_cost = (current / 1000) * 0.002
        
        return ContextPressureEntry(
            session_id=session_data['session_id'],
            agent_id=session_data['agent_id'],
            current_tokens=current,
            threshold=int(limit * self.WARN_THRESHOLD),
            max_context=max_limit,
            pressure_level=level,
            usage_percent=round(usage_percent * 100, 1),
            estimated_cost=round(estimated_cost, 4),
            recommendation=recommendation,
            last_activity=session_data.get('last_activity')
        )
    
    def get_all_sessions_pressure(self, hours: int = 24) -> ContextPressureSnapshot:
        """获取所有session的压力状态"""
        
        entries = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        # 扫描所有Agent的session
        if not self.agents_dir.exists():
            return ContextPressureSnapshot(
                generated_at=datetime.now().isoformat(),
                total_sessions=0,
                ok_count=0,
                warn_count=0,
                critical_count=0,
                entries=[]
            )
        
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
                    
                    # 分析session
                    session_data = self.get_session_context_usage(jsonl_file)
                    if session_data:
                        entry = self.check_pressure(session_data)
                        entries.append(entry)
                        
                except Exception as e:
                    continue
        
        # 统计
        ok_count = sum(1 for e in entries if e.pressure_level == PressureLevel.OK)
        warn_count = sum(1 for e in entries if e.pressure_level == PressureLevel.WARN)
        critical_count = sum(1 for e in entries if e.pressure_level == PressureLevel.CRITICAL)
        
        # 按压力等级排序
        entries.sort(key=lambda x: (
            0 if x.pressure_level == PressureLevel.CRITICAL else
            1 if x.pressure_level == PressureLevel.WARN else 2
        ))
        
        return ContextPressureSnapshot(
            generated_at=datetime.now().isoformat(),
            total_sessions=len(entries),
            ok_count=ok_count,
            warn_count=warn_count,
            critical_count=critical_count,
            entries=entries
        )
    
    def get_pressure_summary(self) -> Dict:
        """获取压力摘要报告"""
        snapshot = self.get_all_sessions_pressure()
        
        # 找出需要关注的session
        critical_sessions = [e for e in snapshot.entries if e.pressure_level == PressureLevel.CRITICAL]
        warn_sessions = [e for e in snapshot.entries if e.pressure_level == PressureLevel.WARN]
        
        # 计算总体风险
        if snapshot.total_sessions == 0:
            overall_risk = "ok"
        elif critical_count := len(critical_sessions) > 0:
            overall_risk = "critical"
        elif len(warn_sessions) > 0:
            overall_risk = "warn"
        else:
            overall_risk = "ok"
        
        # 生成建议
        recommendations = []
        if critical_sessions:
            recommendations.append(f"有 {len(critical_sessions)} 个session即将溢出，建议立即开启新session")
        if warn_sessions:
            recommendations.append(f"有 {len(warn_sessions)} 个session接近限制，建议规划新session")
        
        return {
            "generated_at": snapshot.generated_at,
            "overall_risk": overall_risk,
            "summary": {
                "total_sessions": snapshot.total_sessions,
                "ok": snapshot.ok_count,
                "warn": snapshot.warn_count,
                "critical": snapshot.critical_count
            },
            "critical_sessions": [
                {
                    "session_id": e.session_id,
                    "agent_id": e.agent_id,
                    "usage": f"{e.usage_percent}%",
                    "tokens": e.current_tokens
                } for e in critical_sessions[:5]  # 只显示前5个
            ],
            "recommendations": recommendations
        }


# 测试代码
if __name__ == "__main__":
    print("🎯 Context Pressure Monitor 测试")
    print("="*60)
    
    monitor = ContextPressureMonitor()
    
    # 获取压力快照
    print("\n🔍 分析所有session的上下文压力...")
    snapshot = monitor.get_all_sessions_pressure(hours=24)
    
    print(f"\n📊 压力分布:")
    print(f"  总Session数: {snapshot.total_sessions}")
    print(f"  🟢 正常 (OK): {snapshot.ok_count}")
    print(f"  🟡 警告 (Warn): {snapshot.warn_count}")
    print(f"  🔴 严重 (Critical): {snapshot.critical_count}")
    
    if snapshot.entries:
        print(f"\n📈 压力最高的Session:")
        for entry in snapshot.entries[:10]:
            emoji = "🔴" if entry.pressure_level == PressureLevel.CRITICAL else "🟡" if entry.pressure_level == PressureLevel.WARN else "🟢"
            print(f"\n  {emoji} {entry.session_id[:20]}...")
            print(f"      Agent: {entry.agent_id}")
            print(f"      使用: {entry.usage_percent}% ({entry.current_tokens:,} / {entry.max_context:,} tokens)")
            print(f"      预估成本: ${entry.estimated_cost:.4f}")
            if entry.recommendation:
                print(f"      💡 {entry.recommendation}")
    
    # 摘要报告
    print("\n" + "="*60)
    summary = monitor.get_pressure_summary()
    print(f"📋 整体风险等级: {summary['overall_risk'].upper()}")
    if summary['recommendations']:
        print("\n⚠️  建议操作:")
        for rec in summary['recommendations']:
            print(f"  • {rec}")
    else:
        print("✅ 所有session运行正常")
