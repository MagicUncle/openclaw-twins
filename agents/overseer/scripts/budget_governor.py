#!/usr/bin/env python3
"""
Budget Governor - 预算治理器
提取自 OpenClaw Control Center 的 budget-governance.ts
功能: Token配额管理、成本预警、多层级预算
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class BudgetStatus(str, Enum):
    OK = "ok"
    WARN = "warn"
    OVER = "over"


@dataclass
class BudgetEvaluation:
    """预算评估结果"""
    scope: str  # agent | project | task
    scope_id: str
    used: int
    limit: int
    warn_at: int
    status: BudgetStatus
    usage_percent: float


class BudgetGovernor:
    """预算治理器"""
    
    # 默认配额（可配置）
    DEFAULT_QUOTAS = {
        "agent": {
            "tokens_per_day": 100000,
            "cost_per_day": 5.0  # USD
        },
        "project": {
            "tokens_per_month": 1000000,
            "cost_per_month": 50.0
        }
    }
    
    def __init__(self):
        self.usage_store = {}  # 简化的内存存储
    
    def evaluate_budget(self, scope: str, scope_id: str, 
                       used_tokens: int, limit: int = None) -> BudgetEvaluation:
        """评估预算状态"""
        
        if limit is None:
            limit = self.DEFAULT_QUOTAS.get(scope, {}).get("tokens_per_day", 100000)
        
        warn_at = int(limit * 0.8)  # 80%警告
        usage_percent = (used_tokens / limit) * 100
        
        if used_tokens > limit:
            status = BudgetStatus.OVER
        elif used_tokens > warn_at:
            status = BudgetStatus.WARN
        else:
            status = BudgetStatus.OK
        
        return BudgetEvaluation(
            scope=scope,
            scope_id=scope_id,
            used=used_tokens,
            limit=limit,
            warn_at=warn_at,
            status=status,
            usage_percent=round(usage_percent, 1)
        )
    
    def get_budget_summary(self, agent_usage: Dict[str, int]) -> Dict:
        """获取预算摘要"""
        evaluations = []
        
        for agent_id, used in agent_usage.items():
            eval = self.evaluate_budget("agent", agent_id, used)
            evaluations.append(eval)
        
        ok = sum(1 for e in evaluations if e.status == BudgetStatus.OK)
        warn = sum(1 for e in evaluations if e.status == BudgetStatus.WARN)
        over = sum(1 for e in evaluations if e.status == BudgetStatus.OVER)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "total": len(evaluations),
            "ok": ok,
            "warn": warn,
            "over": over,
            "evaluations": [
                {
                    "scope": e.scope,
                    "scope_id": e.scope_id,
                    "used": e.used,
                    "limit": e.limit,
                    "usage_percent": e.usage_percent,
                    "status": e.status.value
                } for e in evaluations
            ]
        }


if __name__ == "__main__":
    governor = BudgetGovernor()
    
    # 模拟数据
    usage = {
        "zongban": 85000,   # 接近限制
        "main": 45000,      # 正常
        "wenyuan": 120000,  # 超出
    }
    
    summary = governor.get_budget_summary(usage)
    print(f"预算摘要: {summary['ok']}正常, {summary['warn']}警告, {summary['over']}超出")
