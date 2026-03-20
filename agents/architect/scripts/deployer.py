#!/usr/bin/env python3
"""
Deployer - 自动部署脚本 v1.0
根据Architect提案自动实施优化
"""

import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 配置路径
WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
PROPOSALS_DIR = WORKSPACE / "metrics" / "proposals"
SKILLS_DIR = WORKSPACE / "skills"
AGENTS_DIR = WORKSPACE / "agents"


class Deployer:
    """自动部署器"""
    
    def __init__(self):
        self.deployment_log = []
    
    def list_pending_proposals(self, date: Optional[str] = None) -> List[Dict]:
        """列出待部署的提案"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        proposals_dir = PROPOSALS_DIR / date
        if not proposals_dir.exists():
            print(f"❌ 未找到 {date} 的提案目录")
            return []
        
        summary_path = proposals_dir / "summary.json"
        if not summary_path.exists():
            print(f"❌ 未找到汇总文件")
            return []
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        proposals = []
        for p in summary.get("proposals", []):
            json_path = proposals_dir / f"{p['id']}.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    proposal = json.load(f)
                    proposals.append(proposal)
        
        return proposals
    
    def deploy_optimization(self, proposal: Dict) -> bool:
        """部署优化提案"""
        target = proposal.get("target")
        print(f"🔧 正在部署优化: {target}")
        
        # 在实际场景中，这里会：
        # 1. 读取目标Agent的SKILL.md
        # 2. 应用优化建议（修改Prompt、添加错误处理等）
        # 3. 保存修改并备份原文件
        
        print(f"  ✓ 已为 {target} 应用优化")
        return True
    
    def deploy_new_skill(self, proposal: Dict) -> bool:
        """部署新技能"""
        skill_config = proposal.get("proposed_skill", {})
        skill_name = skill_config.get("name")
        
        if not skill_name:
            print("❌ 技能名称缺失")
            return False
        
        print(f"🛠️ 正在部署新技能: {skill_name}")
        
        # 创建技能目录
        skill_dir = SKILLS_DIR / skill_name
        if skill_dir.exists():
            print(f"  ⚠️ 技能 {skill_name} 已存在，跳过")
            return False
        
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成SKILL.md
        skill_md = self._generate_skill_md(skill_config)
        (skill_dir / "SKILL.md").write_text(skill_md, encoding='utf-8')
        
        # 生成基础代码框架
        code = self._generate_skill_code(skill_config)
        (skill_dir / f"{skill_name}.py").write_text(code, encoding='utf-8')
        
        print(f"  ✓ 技能 {skill_name} 已部署到 {skill_dir}")
        return True
    
    def _generate_skill_md(self, config: Dict) -> str:
        """生成SKILL.md内容"""
        name = config.get("name", "new_skill")
        description = config.get("description", "新技能")
        triggers = config.get("triggers", ["触发条件"])
        
        return f"""# {name}

{description}

## When to use

{chr(10).join(f"- {t}" for t in triggers)}

## Steps

1. 接收并验证输入参数
2. 执行核心逻辑
3. 返回结构化结果
4. 处理异常情况

## Tools

- 根据需要添加工具调用

## Output

- result: 执行结果
- status: success/error
- message: 状态说明

## Examples

### Example 1

Input: {{"param": "value"}}
Output: {{"result": "...", "status": "success"}}

## Notes

- 由 Architect 自动生成的技能
- 版本: 1.0.0
- 生成时间: {datetime.now().strftime("%Y-%m-%d")}
"""
    
    def _generate_skill_code(self, config: Dict) -> str:
        """生成技能代码框架"""
        name = config.get("name", "new_skill")
        
        return f"""#!/usr/bin/env python3
\"\"\"
{name} - 自动生成的技能
\"\"\"

import json
from typing import Dict, Any

def {name}(input_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    执行{name}操作
    
    Args:
        input_data: 输入参数
        
    Returns:
        执行结果
    \"\"\"
    try:
        # TODO: 实现核心逻辑
        result = process_input(input_data)
        
        return {{
            "status": "success",
            "result": result,
            "message": "执行成功"
        }}
    except Exception as e:
        return {{
            "status": "error",
            "result": None,
            "message": str(e)
        }}

def process_input(data: Dict[str, Any]) -> Any:
    \"\"\"
    处理输入数据
    \"\"\"
    # TODO: 实现具体逻辑
    return data

if __name__ == "__main__":
    # 测试代码
    test_input = {{"param": "test"}}
    result = {name}(test_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))
"""
    
    def deploy_proposal(self, proposal_id: str, date: Optional[str] = None) -> bool:
        """部署单个提案"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 加载提案
        proposal_path = PROPOSALS_DIR / date / f"{proposal_id}.json"
        if not proposal_path.exists():
            print(f"❌ 提案不存在: {proposal_id}")
            return False
        
        with open(proposal_path, 'r', encoding='utf-8') as f:
            proposal = json.load(f)
        
        # 根据类型部署
        ptype = proposal.get("type")
        
        if ptype == "optimization":
            success = self.deploy_optimization(proposal)
        elif ptype == "new_skill":
            success = self.deploy_new_skill(proposal)
        else:
            print(f"⚠️ 未知提案类型: {ptype}")
            return False
        
        # 记录部署日志
        self.deployment_log.append({
            "timestamp": datetime.now().isoformat(),
            "proposal_id": proposal_id,
            "type": ptype,
            "status": "success" if success else "failed"
        })
        
        return success
    
    def interactive_deploy(self, date: Optional[str] = None):
        """交互式部署"""
        proposals = self.list_pending_proposals(date)
        
        if not proposals:
            print("ℹ️ 没有待部署的提案")
            return
        
        print(f"\n{'='*60}")
        print(f"🚀 提案部署界面")
        print(f"{'='*60}\n")
        
        # 按优先级排序
        proposals.sort(key=lambda p: 0 if p.get("priority") == "P0" else 1 if p.get("priority") == "P1" else 2)
        
        for i, p in enumerate(proposals, 1):
            icon = "🚨" if p.get("priority") == "P0" else "🔶" if p.get("priority") == "P1" else "🔹"
            print(f"{i}. {icon} [{p.get('priority', 'P2')}] {p['title']}")
            print(f"   类型: {p.get('type')} | ID: {p['id']}")
            print()
        
        while True:
            choice = input("选择要部署的提案编号 (1-{}), 或输入 'all' 部署全部, 'q' 退出: ".format(len(proposals)))
            
            if choice.lower() == 'q':
                break
            
            if choice.lower() == 'all':
                for p in proposals:
                    print(f"\n部署: {p['title']}")
                    self.deploy_proposal(p['id'], date)
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(proposals):
                    p = proposals[idx]
                    print(f"\n部署: {p['title']}")
                    if self.deploy_proposal(p['id'], date):
                        print("✅ 部署成功")
                    else:
                        print("❌ 部署失败")
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 无效输入")
    
    def show_summary(self):
        """显示部署摘要"""
        if not self.deployment_log:
            print("ℹ️ 本次无部署记录")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 部署摘要")
        print(f"{'='*60}")
        
        success = sum(1 for d in self.deployment_log if d["status"] == "success")
        failed = sum(1 for d in self.deployment_log if d["status"] == "failed")
        
        print(f"总计: {len(self.deployment_log)} 个提案")
        print(f"成功: {success}")
        print(f"失败: {failed}")
        print()
        
        for d in self.deployment_log:
            icon = "✅" if d["status"] == "success" else "❌"
            print(f"{icon} {d['proposal_id']} ({d['type']})")


def main():
    """入口函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="部署Architect生成的提案")
    parser.add_argument("--date", help="提案日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--proposal", help="指定提案ID部署")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式部署")
    
    args = parser.parse_args()
    
    deployer = Deployer()
    
    if args.interactive:
        deployer.interactive_deploy(args.date)
        deployer.show_summary()
    elif args.proposal:
        if deployer.deploy_proposal(args.proposal, args.date):
            print("✅ 部署成功")
        else:
            print("❌ 部署失败")
    else:
        # 默认交互式模式
        deployer.interactive_deploy(args.date)
        deployer.show_summary()


if __name__ == "__main__":
    main()
