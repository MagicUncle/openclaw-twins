"""
Proposal Manager - 完整提案管理模块
提供提案的CRUD和审批操作
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

class ProposalManager:
    """提案管理器"""
    
    def __init__(self):
        self.proposals_dir = Path("/Users/magicuncle/.openclaw/workspace/metrics/proposals")
        self.db_path = Path("/Users/magicuncle/.openclaw/workspace/saas/proposal_states.json")
        self._load_states()
    
    def _load_states(self):
        """加载提案状态"""
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                self.states = json.load(f)
        else:
            self.states = {}
    
    def _save_states(self):
        """保存提案状态"""
        with open(self.db_path, 'w') as f:
            json.dump(self.states, f, indent=2)
    
    def get_all_proposals(self) -> List[Dict]:
        """获取所有提案"""
        proposals = []
        
        # 遍历所有日期目录
        for date_dir in self.proposals_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            summary_file = date_dir / "summary.json"
            if not summary_file.exists():
                continue
            
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            for prop_summary in summary.get("proposals", []):
                proposal_id = prop_summary["id"]
                
                # 读取完整提案
                detail_file = date_dir / f"{proposal_id}.json"
                if detail_file.exists():
                    with open(detail_file, 'r') as f:
                        detail = json.load(f)
                    
                    # 合并状态
                    detail["_status"] = self.states.get(proposal_id, "pending")
                    detail["_date"] = date_dir.name
                    proposals.append(detail)
        
        # 按时间倒序
        proposals.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return proposals
    
    def get_proposal_detail(self, proposal_id: str) -> Optional[Dict]:
        """获取提案详情"""
        # 查找提案文件
        for date_dir in self.proposals_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            detail_file = date_dir / f"{proposal_id}.json"
            if detail_file.exists():
                with open(detail_file, 'r') as f:
                    detail = json.load(f)
                
                # 添加状态
                detail["_status"] = self.states.get(proposal_id, "pending")
                detail["_date"] = date_dir.name
                
                # 添加风险分析（如果没有）
                if "risks" not in detail:
                    detail["risks"] = self._analyze_risks(detail)
                
                return detail
        
        return None
    
    def _analyze_risks(self, proposal: Dict) -> List[Dict]:
        """分析提案风险"""
        risks = []
        
        ptype = proposal.get("type", "")
        effort = proposal.get("effort", "medium")
        
        # 根据类型和复杂度分析风险
        if effort == "high":
            risks.append({
                "level": "medium",
                "description": "实施工作量较大，可能需要较长时间",
                "mitigation": "建议分阶段实施，先进行小规模测试"
            })
        
        if ptype == "optimization":
            risks.append({
                "level": "low", 
                "description": "优化可能影响现有功能",
                "mitigation": "建议在测试环境验证后再部署到生产环境"
            })
        
        if ptype == "new_skill":
            risks.append({
                "level": "medium",
                "description": "新技能可能引入未预期的行为",
                "mitigation": "建议先进行充分的单元测试和集成测试"
            })
        
        if not risks:
            risks.append({
                "level": "low",
                "description": "风险可控",
                "mitigation": "按标准流程实施即可"
            })
        
        return risks
    
    def approve_proposal(self, proposal_id: str) -> bool:
        """批准提案"""
        if proposal_id not in self.states:
            self.states[proposal_id] = "approved"
            self._save_states()
            
            # 记录审批日志
            self._log_action(proposal_id, "approved")
            return True
        return False
    
    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """拒绝提案"""
        if proposal_id not in self.states:
            self.states[proposal_id] = "rejected"
            self._save_states()
            
            # 记录拒绝日志
            self._log_action(proposal_id, "rejected", reason)
            return True
        return False
    
    def apply_proposal(self, proposal_id: str) -> bool:
        """应用提案"""
        if self.states.get(proposal_id) == "approved":
            self.states[proposal_id] = "applied"
            self._save_states()
            
            # 记录应用日志
            self._log_action(proposal_id, "applied")
            return True
        return False
    
    def _log_action(self, proposal_id: str, action: str, reason: str = ""):
        """记录操作日志"""
        log_file = Path("/Users/magicuncle/.openclaw/workspace/saas/proposal_actions.log")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "proposal_id": proposal_id,
            "action": action,
            "reason": reason
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def get_statistics(self) -> Dict:
        """获取提案统计"""
        proposals = self.get_all_proposals()
        
        total = len(proposals)
        pending = sum(1 for p in proposals if p.get("_status") == "pending")
        approved = sum(1 for p in proposals if p.get("_status") == "approved")
        applied = sum(1 for p in proposals if p.get("_status") == "applied")
        rejected = sum(1 for p in proposals if p.get("_status") == "rejected")
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "applied": applied,
            "rejected": rejected
        }


# 单例
_proposal_manager = None

def get_proposal_manager() -> ProposalManager:
    """获取提案管理器实例"""
    global _proposal_manager
    if _proposal_manager is None:
        _proposal_manager = ProposalManager()
    return _proposal_manager


if __name__ == "__main__":
    manager = get_proposal_manager()
    
    print("📋 提案管理系统测试")
    print("="*60)
    
    # 获取所有提案
    proposals = manager.get_all_proposals()
    print(f"\n✅ 找到 {len(proposals)} 个提案")
    
    # 统计
    stats = manager.get_statistics()
    print(f"\n📊 统计:")
    print(f"  总计: {stats['total']}")
    print(f"  待处理: {stats['pending']}")
    print(f"  已批准: {stats['approved']}")
    print(f"  已应用: {stats['applied']}")
    print(f"  已拒绝: {stats['rejected']}")
    
    # 显示第一个提案详情
    if proposals:
        first = proposals[0]
        print(f"\n📄 第一个提案:")
        print(f"  ID: {first['id']}")
        print(f"  标题: {first['title']}")
        print(f"  状态: {first['_status']}")
        print(f"  解决方案: {len(first.get('solutions', []))} 个")
        
        # 风险分析
        if 'risks' in first:
            print(f"\n⚠️  风险分析:")
            for risk in first['risks']:
                print(f"  - [{risk['level']}] {risk['description']}")
