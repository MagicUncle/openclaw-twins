#!/usr/bin/env python3
"""
System Operation Visualizer - 系统运行状态可视化
展示Overseer和Architect的自动运行、自探索、自进化能力
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class SystemOperationVisualizer:
    """系统运行状态可视化器"""
    
    def __init__(self):
        self.workspace = Path("/Users/magicuncle/.openclaw/workspace")
        self.metrics_dir = self.workspace / "metrics"
        self.agents_dir = self.workspace / "agents"
        
    def get_overseer_status(self) -> dict:
        """获取Overseer监控状态"""
        
        # 读取最近的监控报告
        daily_dir = self.metrics_dir / "daily"
        reports = sorted(daily_dir.glob("*.json"), reverse=True) if daily_dir.exists() else []
        
        latest_report = None
        if reports:
            with open(reports[0], 'r') as f:
                latest_report = json.load(f)
        
        # 检查执行日志
        execution_log = self.agents_dir / "overseer" / "data" / "execution.log"
        last_run = None
        total_runs = 0
        
        if execution_log.exists():
            with open(execution_log, 'r') as f:
                lines = f.readlines()
                total_runs = len(lines)
                if lines:
                    try:
                        last_entry = json.loads(lines[-1])
                        last_run = last_entry.get("timestamp")
                    except:
                        pass
        
        # 判断运行状态
        if last_run:
            last_time = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
            time_diff = datetime.now() - last_time
            is_healthy = time_diff < timedelta(hours=24)
        else:
            is_healthy = False
        
        return {
            "agent_name": "Overseer (监控优化师)",
            "status": "running" if is_healthy else "stopped",
            "last_run": last_run,
            "total_executions": total_runs,
            "schedule": "每12小时自动执行",
            "next_run": (datetime.fromisoformat(last_run.replace('Z', '+00:00')) + timedelta(hours=12)).isoformat() if last_run else None,
            "capabilities": [
                "自动采集所有Agent活动数据",
                "计算效能评分和分级",
                "生成监控报告",
                "识别异常和瓶颈"
            ],
            "latest_report": latest_report,
            "health": "healthy" if is_healthy else "warning"
        }
    
    def get_architect_status(self) -> dict:
        """获取Architect进化状态"""
        
        # 读取提案
        proposals_dir = self.metrics_dir / "proposals"
        all_proposals = []
        
        if proposals_dir.exists():
            for date_dir in proposals_dir.iterdir():
                if date_dir.is_dir():
                    for proposal_file in date_dir.glob("*.json"):
                        if proposal_file.name != "summary.json":
                            try:
                                with open(proposal_file, 'r') as f:
                                    prop = json.load(f)
                                    prop["_date"] = date_dir.name
                                    all_proposals.append(prop)
                            except:
                                pass
        
        # 统计
        pending = [p for p in all_proposals if p.get("status") == "pending"]
        approved = [p for p in all_proposals if p.get("status") == "approved"]
        applied = [p for p in all_proposals if p.get("status") == "applied"]
        
        # 检查执行日志
        execution_log = self.agents_dir / "architect" / "data" / "execution.log"
        last_run = None
        total_runs = 0
        
        if execution_log.exists():
            with open(execution_log, 'r') as f:
                lines = f.readlines()
                total_runs = len(lines)
                if lines:
                    try:
                        last_entry = json.loads(lines[-1])
                        last_run = last_entry.get("timestamp")
                    except:
                        pass
        
        # 读取学习笔记
        notes_file = self.agents_dir / "architect" / "data" / "daily_notes" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        has_learning_notes = notes_file.exists()
        
        return {
            "agent_name": "Architect (进化导师)",
            "status": "running" if last_run else "stopped",
            "last_run": last_run,
            "total_executions": total_runs,
            "schedule": "每天9:00自动执行",
            "next_run": (datetime.fromisoformat(last_run.replace('Z', '+00:00')) + timedelta(days=1)).isoformat() if last_run else None,
            "capabilities": [
                "读取Overseer报告识别能力缺口",
                "搜索外部最佳实践",
                "生成优化提案",
                "自动部署（需审批）",
                "持续学习沉淀"
            ],
            "proposals": {
                "total": len(all_proposals),
                "pending": len(pending),
                "approved": len(approved),
                "applied": len(applied),
                "recent": all_proposals[:5]
            },
            "learning": {
                "has_notes": has_learning_notes,
                "notes_path": str(notes_file) if has_learning_notes else None
            },
            "health": "healthy" if last_run and (datetime.now() - datetime.fromisoformat(last_run.replace('Z', '+00:00'))) < timedelta(days=2) else "warning"
        }
    
    def get_evolution_timeline(self) -> list:
        """获取进化时间线"""
        timeline = []
        
        # 从优化日志读取
        opt_log = self.workspace / "saas" / "optimization_log.jsonl"
        if opt_log.exists():
            with open(opt_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        timeline.append({
                            "time": entry.get("timestamp"),
                            "type": "optimization",
                            "agent": entry.get("target"),
                            "action": "应用优化",
                            "solutions": entry.get("solutions_applied", [])
                        })
                    except:
                        pass
        
        # 从部署记录读取
        deploy_log = self.workspace / "saas" / "deployment_log.json"
        if deploy_log.exists():
            try:
                with open(deploy_log, 'r') as f:
                    deployments = json.load(f)
                    for dep in deployments[-10:]:  # 最近10个
                        timeline.append({
                            "time": dep.get("deployed_at"),
                            "type": "deployment",
                            "agent": dep.get("agent_name"),
                            "action": "部署新技能"
                        })
            except:
                pass
        
        return sorted(timeline, key=lambda x: x.get("time", ""), reverse=True)[:20]
    
    def get_full_system_status(self) -> dict:
        """获取完整系统运行状态"""
        
        return {
            "generated_at": datetime.now().isoformat(),
            "overseer": self.get_overseer_status(),
            "architect": self.get_architect_status(),
            "evolution_timeline": self.get_evolution_timeline(),
            "system_health": {
                "overseer_healthy": self.get_overseer_status()["health"] == "healthy",
                "architect_healthy": self.get_architect_status()["health"] == "healthy",
                "auto_monitoring_enabled": True,
                "auto_evolution_enabled": True
            }
        }

# 测试
if __name__ == "__main__":
    visualizer = SystemOperationVisualizer()
    status = visualizer.get_full_system_status()
    
    print("🎯 系统运行状态可视化")
    print("="*60)
    
    print("\n📊 Overseer 状态:")
    overseer = status["overseer"]
    print(f"  状态: {overseer['status']}")
    print(f"  总执行次数: {overseer['total_executions']}")
    print(f"  能力: {len(overseer['capabilities'])} 项")
    
    print("\n🏗️ Architect 状态:")
    architect = status["architect"]
    print(f"  状态: {architect['status']}")
    print(f"  提案: {architect['proposals']['total']} 个")
    print(f"    - 待处理: {architect['proposals']['pending']}")
    print(f"    - 已批准: {architect['proposals']['approved']}")
    print(f"    - 已应用: {architect['proposals']['applied']}")
    
    print("\n📈 进化时间线:")
    for item in status["evolution_timeline"][:5]:
        print(f"  • {item['time'][:16]}: {item['action']} ({item['agent']})")
    
    print("\n✅ 系统健康:")
    health = status["system_health"]
    print(f"  Overseer: {'健康' if health['overseer_healthy'] else '异常'}")
    print(f"  Architect: {'健康' if health['architect_healthy'] else '异常'}")
    print(f"  自动监控: {'已启用' if health['auto_monitoring_enabled'] else '已禁用'}")
    print(f"  自动进化: {'已启用' if health['auto_evolution_enabled'] else '已禁用'}")
