#!/usr/bin/env python3
"""
Architect - 进化导师核心脚本 v1.0
自动分析系统缺口，搜索解决方案，生成优化提案
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

# 配置路径
WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
METRICS_DIR = WORKSPACE / "metrics"
DAILY_DIR = METRICS_DIR / "daily"
PROPOSALS_DIR = METRICS_DIR / "proposals"
ARCHITECT_DIR = WORKSPACE / "agents" / "architect"
DATA_DIR = ARCHITECT_DIR / "data"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"

# 确保目录存在
for d in [PROPOSALS_DIR, DATA_DIR, KNOWLEDGE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Architect:
    """进化导师核心类"""
    
    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        self.overseer_report: Optional[Dict] = None
        self.gaps: List[Dict] = []
        self.proposals: List[Dict] = []
        
    def load_overseer_report(self) -> Optional[Dict]:
        """加载Overseer的监控报告"""
        print("📊 正在加载Overseer报告...")
        
        # 尝试加载昨日报告
        report_path = DAILY_DIR / f"{self.yesterday}.json"
        
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                self.overseer_report = json.load(f)
            print(f"✅ 已加载 {self.yesterday} 的报告")
            return self.overseer_report
        
        # 尝试加载今日报告（Overseer已提前执行）
        report_path = DAILY_DIR / f"{self.today}.json"
        if report_path.exists():
            with open(report_path, 'r', encoding='utf-8') as f:
                self.overseer_report = json.load(f)
            print(f"✅ 已加载 {self.today} 的报告")
            return self.overseer_report
        
        # 尝试加载最近可用的报告
        available_reports = sorted(DAILY_DIR.glob("*.json"), reverse=True)
        if available_reports:
            with open(available_reports[0], 'r', encoding='utf-8') as f:
                self.overseer_report = json.load(f)
            print(f"⚠️ 使用历史报告: {available_reports[0].name}")
            return self.overseer_report
        
        print("❌ 未找到Overseer报告，无法继续分析")
        return None
    
    def identify_gaps(self) -> List[Dict]:
        """识别系统能力缺口"""
        print("🔍 正在识别能力缺口...")
        
        if not self.overseer_report:
            return []
        
        gaps = []
        agents = self.overseer_report.get("agents", {})
        
        # 1. 低性能Agent
        for agent_name, stats in agents.items():
            if stats.get("grade") == "C":
                gaps.append({
                    "id": f"gap-low-perf-{agent_name}",
                    "type": "low_performance",
                    "agent": agent_name,
                    "severity": "high",
                    "description": f"{agent_name} 被评为C级，效能分仅 {stats.get('efficiency_score', 0)}",
                    "metrics": {
                        "efficiency_score": stats.get("efficiency_score"),
                        "success_rate": stats.get("success_rate"),
                        "calls": stats.get("calls")
                    },
                    "search_query": f"{agent_name} agent optimization best practices"
                })
        
        # 2. 低成功率Agent
        for agent_name, stats in agents.items():
            if stats.get("success_rate", 1.0) < 0.7 and stats.get("grade") != "C":
                gaps.append({
                    "id": f"gap-low-success-{agent_name}",
                    "type": "low_success_rate",
                    "agent": agent_name,
                    "severity": "high",
                    "description": f"{agent_name} 成功率仅 {stats.get('success_rate', 0):.1%}，需要修复错误处理",
                    "metrics": {
                        "success_rate": stats.get("success_rate"),
                        "errors": stats.get("errors", [])
                    },
                    "search_query": f"{agent_name} error handling retry logic best practice"
                })
        
        # 3. 高成本Agent
        sorted_by_cost = sorted(agents.items(), key=lambda x: x[1].get("total_tokens", 0), reverse=True)
        for agent_name, stats in sorted_by_cost[:2]:  # Top 2
            if stats.get("total_tokens", 0) > 5000:  # Token阈值
                gaps.append({
                    "id": f"gap-high-cost-{agent_name}",
                    "type": "high_cost",
                    "agent": agent_name,
                    "severity": "medium",
                    "description": f"{agent_name} 消耗 {stats.get('total_tokens', 0)} tokens，需要成本优化",
                    "metrics": {
                        "total_tokens": stats.get("total_tokens"),
                        "avg_tokens": stats.get("avg_input_tokens", 0) + stats.get("avg_output_tokens", 0)
                    },
                    "search_query": f"{agent_name} token optimization caching strategy"
                })
        
        # 4. 缺失的工具能力（检查系统中实际安装的技能）
        # 获取已安装的技能列表
        skills_dir = WORKSPACE / "skills"
        installed_skills = set()
        if skills_dir.exists():
            for item in skills_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    installed_skills.add(item.name)
        
        # 技能名称映射（工具名 -> 技能目录名）
        tool_to_skill = {
            "browser": "agent-browser",
            "tavily": "tavily-search", 
            "code_execute": None,  # 暂未实现
            "file_write": None     # 暂未实现
        }
        
        # 检查缺失的工具能力
        for tool, skill_name in tool_to_skill.items():
            if skill_name and skill_name not in installed_skills:
                gaps.append({
                    "id": f"gap-missing-tool-{tool}",
                    "type": "missing_capability",
                    "capability": tool,
                    "severity": "medium",
                    "description": f"系统缺少 {tool} 工具能力，建议添加对应skill",
                    "search_query": f"openclaw {tool} skill implementation github"
                })
        
        # 记录已安装的技能（用于日志）
        installed_list = [s for s in [tool_to_skill.get(t) for t in tool_to_skill] if s]
        found = installed_skills & set(installed_list)
        if found:
            print(f"  ✓ 已安装技能: {', '.join(found)}")
        
        self.gaps = gaps
        print(f"✅ 识别到 {len(gaps)} 个能力缺口")
        for gap in gaps:
            print(f"  - [{gap['severity'].upper()}] {gap['type']}: {gap.get('agent') or gap.get('capability')}")
        
        return gaps
    
    async def search_solutions(self, gap: Dict) -> List[Dict]:
        """使用Tavily搜索解决方案"""
        query = gap.get("search_query", "")
        if not query:
            return []
        
        print(f"🔍 搜索: {query}")
        
        try:
            # 调用tavily搜索
            # 使用node执行tavily search脚本
            tavily_script = WORKSPACE / "skills" / "tavily-search" / "scripts" / "search.mjs"
            
            if tavily_script.exists():
                result = subprocess.run(
                    ["node", str(tavily_script), query, "-n", "3"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # 解析tavily输出（假设是JSON格式）
                    try:
                        results = json.loads(result.stdout)
                        print(f"  ✓ 找到 {len(results)} 个结果")
                        return results
                    except:
                        # 如果不是JSON，保存原始输出
                        return [{"raw_output": result.stdout}]
                else:
                    print(f"  ⚠️ Tavily搜索失败: {result.stderr}")
                    return []
            else:
                # 模拟搜索结果（用于测试）
                print(f"  ℹ️ Tavily脚本未找到，使用模拟数据")
                return self._mock_search_results(gap)
                
        except Exception as e:
            print(f"  ⚠️ 搜索异常: {e}")
            return []
    
    def _mock_search_results(self, gap: Dict) -> List[Dict]:
        """生成模拟搜索结果用于测试"""
        gap_type = gap.get("type", "")
        
        if "optimization" in gap_type or "performance" in gap_type:
            return [
                {
                    "title": "Agent Performance Optimization Guide",
                    "url": "https://github.com/example/agent-optimization",
                    "snippet": "Best practices for improving agent efficiency and reducing token consumption"
                },
                {
                    "title": "Prompt Engineering for Better Results",
                    "url": "https://blog.example.com/prompt-engineering",
                    "snippet": "Techniques to improve agent success rates through better prompts"
                }
            ]
        elif "missing" in gap_type:
            return [
                {
                    "title": f"{gap.get('capability', 'Tool')} Implementation Example",
                    "url": f"https://github.com/example/{gap.get('capability', 'tool')}-skill",
                    "snippet": f"Reference implementation for {gap.get('capability', 'tool')} functionality"
                }
            ]
        else:
            return [
                {
                    "title": "Multi-Agent System Best Practices",
                    "url": "https://github.com/example/multi-agent-patterns",
                    "snippet": "Patterns and architectures for building efficient agent systems"
                }
            ]
    
    def generate_proposals(self) -> List[Dict]:
        """基于缺口和搜索结果生成提案"""
        print("💡 正在生成优化提案...")
        
        proposals = []
        
        for gap in self.gaps:
            # 根据缺口类型生成不同类型的提案
            if gap["type"] == "low_performance":
                proposal = self._generate_optimization_proposal(gap)
                proposals.append(proposal)
                
            elif gap["type"] == "low_success_rate":
                proposal = self._generate_error_handling_proposal(gap)
                proposals.append(proposal)
                
            elif gap["type"] == "high_cost":
                proposal = self._generate_cost_optimization_proposal(gap)
                proposals.append(proposal)
                
            elif gap["type"] == "missing_capability":
                proposal = self._generate_new_skill_proposal(gap)
                proposals.append(proposal)
        
        self.proposals = proposals
        print(f"✅ 生成 {len(proposals)} 个提案")
        return proposals
    
    def _generate_optimization_proposal(self, gap: Dict) -> Dict:
        """生成优化提案"""
        agent = gap["agent"]
        
        return {
            "id": f"opt-{agent}-{self.today}",
            "type": "optimization",
            "created_at": datetime.now().isoformat(),
            "target": agent,
            "title": f"优化 {agent} 的效能",
            "problem": gap["description"],
            "problem_metrics": gap.get("metrics", {}),
            "solutions": [
                {
                    "name": "Prompt优化",
                    "description": "重构系统提示，增加示例和约束，提升输出质量",
                    "steps": ["分析当前Prompt问题", "添加Few-shot示例", "增加输出格式约束"],
                    "effort": "low",
                    "expected_improvement": "成功率提升10-15%"
                },
                {
                    "name": "工具链优化",
                    "description": "优化工具调用顺序，减少冗余调用",
                    "steps": ["分析工具调用序列", "识别冗余调用", "重构调用逻辑"],
                    "effort": "medium",
                    "expected_improvement": "Token消耗减少20-30%"
                },
                {
                    "name": "添加缓存机制",
                    "description": "缓存重复查询结果，减少重复计算",
                    "steps": ["识别高频重复查询", "实现结果缓存", "添加缓存失效策略"],
                    "effort": "medium",
                    "expected_improvement": "响应时间减少40-50%"
                }
            ],
            "references": gap.get("search_results", []),
            "priority": "P0" if gap["severity"] == "high" else "P1",
            "effort": "medium",
            "impact": "high",
            "auto_apply": False,
            "requires_approval": True
        }
    
    def _generate_error_handling_proposal(self, gap: Dict) -> Dict:
        """生成错误处理优化提案"""
        agent = gap["agent"]
        
        return {
            "id": f"fix-{agent}-{self.today}",
            "type": "error_handling",
            "created_at": datetime.now().isoformat(),
            "target": agent,
            "title": f"修复 {agent} 的错误处理问题",
            "problem": gap["description"],
            "problem_metrics": gap.get("metrics", {}),
            "solutions": [
                {
                    "name": "添加重试机制",
                    "description": "对失败操作进行指数退避重试",
                    "steps": ["识别可重试操作", "实现重试装饰器", "配置退避策略"],
                    "effort": "low",
                    "expected_improvement": "成功率提升15-20%"
                },
                {
                    "name": "增强错误处理",
                    "description": "捕获并优雅处理各类异常",
                    "steps": ["分析常见错误类型", "添加try-catch块", "提供用户友好错误信息"],
                    "effort": "low",
                    "expected_improvement": "减少未处理异常90%"
                }
            ],
            "priority": "P0",
            "effort": "low",
            "impact": "high",
            "auto_apply": False,
            "requires_approval": True
        }
    
    def _generate_cost_optimization_proposal(self, gap: Dict) -> Dict:
        """生成成本优化提案"""
        agent = gap["agent"]
        
        return {
            "id": f"cost-{agent}-{self.today}",
            "type": "cost_optimization",
            "created_at": datetime.now().isoformat(),
            "target": agent,
            "title": f"优化 {agent} 的Token成本",
            "problem": gap["description"],
            "problem_metrics": gap.get("metrics", {}),
            "solutions": [
                {
                    "name": "上下文压缩",
                    "description": "优化Prompt长度，减少不必要的上下文",
                    "steps": ["分析当前Prompt结构", "移除冗余信息", "使用更简洁的表达"],
                    "effort": "low",
                    "expected_improvement": "Token消耗减少25-35%"
                },
                {
                    "name": "模型降级策略",
                    "description": "简单任务使用轻量模型",
                    "steps": ["识别简单任务类型", "实现模型路由逻辑", "配置降级阈值"],
                    "effort": "medium",
                    "expected_improvement": "成本减少40-50%"
                }
            ],
            "priority": "P1",
            "effort": "low",
            "impact": "medium",
            "auto_apply": False,
            "requires_approval": True
        }
    
    def _generate_new_skill_proposal(self, gap: Dict) -> Dict:
        """生成新技能提案"""
        capability = gap["capability"]
        
        return {
            "id": f"skill-{capability}-{self.today}",
            "type": "new_skill",
            "created_at": datetime.now().isoformat(),
            "title": f"添加 {capability} 技能",
            "problem": gap["description"],
            "proposed_skill": {
                "name": capability,
                "description": f"提供{capability}能力的封装",
                "triggers": [f"需要执行{capability}操作时"],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "操作参数"}
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string", "description": "执行结果"}
                    }
                }
            },
            "use_cases": [
                f"自动化{capability}任务",
                f"批量处理{capability}请求"
            ],
            "implementation_guide": [
                f"1. 创建 skills/{capability}/ 目录",
                f"2. 编写 SKILL.md 定义接口",
                f"3. 实现 {capability}.py 核心逻辑",
                f"4. 添加测试用例",
                f"5. 注册到系统"
            ],
            "references": gap.get("search_results", []),
            "priority": "P1",
            "effort": "medium",
            "impact": "high",
            "auto_apply": False,
            "requires_approval": True
        }
    
    def save_proposals(self):
        """保存提案到文件系统"""
        print("💾 正在保存提案...")
        
        # 创建日期目录
        date_dir = PROPOSALS_DIR / self.today
        date_dir.mkdir(exist_ok=True)
        
        # 保存每个提案
        for proposal in self.proposals:
            # JSON格式
            json_path = date_dir / f"{proposal['id']}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(proposal, f, indent=2, ensure_ascii=False)
            
            # Markdown格式
            md_path = date_dir / f"{proposal['id']}.md"
            self._generate_proposal_markdown(proposal, md_path)
        
        # 保存汇总
        summary = {
            "date": self.today,
            "generated_at": datetime.now().isoformat(),
            "total_proposals": len(self.proposals),
            "by_type": {},
            "by_priority": {},
            "proposals": [{"id": p["id"], "title": p["title"], "priority": p.get("priority", "P2")} for p in self.proposals]
        }
        
        for p in self.proposals:
            p_type = p.get("type", "unknown")
            p_priority = p.get("priority", "P2")
            summary["by_type"][p_type] = summary["by_type"].get(p_type, 0) + 1
            summary["by_priority"][p_priority] = summary["by_priority"].get(p_priority, 0) + 1
        
        summary_path = date_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已保存 {len(self.proposals)} 个提案到 {date_dir}")
        return date_dir
    
    def _generate_proposal_markdown(self, proposal: Dict, path: Path):
        """生成提案的Markdown版本"""
        content = f"""# {proposal['title']}

**提案ID**: {proposal['id']}  
**类型**: {proposal['type']}  
**优先级**: {proposal.get('priority', 'P2')}  
**生成时间**: {proposal['created_at']}

---

## 🎯 问题描述

{proposal.get('problem', 'N/A')}

"""
        
        # 添加问题指标
        if 'problem_metrics' in proposal:
            content += "### 相关指标\n\n"
            for key, value in proposal['problem_metrics'].items():
                content += f"- **{key}**: {value}\n"
            content += "\n"
        
        # 添加解决方案
        if 'solutions' in proposal:
            content += "## 💡 建议方案\n\n"
            for i, solution in enumerate(proposal['solutions'], 1):
                content += f"### 方案{i}: {solution['name']}\n\n"
                content += f"**描述**: {solution['description']}\n\n"
                content += f"**工作量**: {solution.get('effort', 'medium')}  "
                content += f"**预期改进**: {solution.get('expected_improvement', '待评估')}\n\n"
                content += "**实施步骤**:\n"
                for step in solution.get('steps', []):
                    content += f"1. {step}\n"
                content += "\n"
        
        # 添加技能规格（如果是新技能提案）
        if 'proposed_skill' in proposal:
            skill = proposal['proposed_skill']
            content += "## 🛠️ 建议技能规格\n\n"
            content += f"**名称**: {skill['name']}\n\n"
            content += f"**描述**: {skill['description']}\n\n"
            content += "**触发条件**:\n"
            for trigger in skill.get('triggers', []):
                content += f"- {trigger}\n"
            content += "\n"
            
            if 'use_cases' in proposal:
                content += "**使用场景**:\n"
                for case in proposal['use_cases']:
                    content += f"- {case}\n"
                content += "\n"
            
            if 'implementation_guide' in proposal:
                content += "## 📋 实施指南\n\n"
                for step in proposal['implementation_guide']:
                    content += f"{step}\n"
                content += "\n"
        
        # 添加参考资源
        if 'references' in proposal and proposal['references']:
            content += "## 📚 参考资源\n\n"
            for ref in proposal['references']:
                if isinstance(ref, dict):
                    title = ref.get('title', ref.get('url', 'Unknown'))
                    url = ref.get('url', '')
                    snippet = ref.get('snippet', '')
                    content += f"- [{title}]({url})\n"
                    if snippet:
                        content += f"  - {snippet}\n"
                else:
                    content += f"- {ref}\n"
            content += "\n"
        
        # 添加决策信息
        content += "## ⚖️ 决策信息\n\n"
        content += f"| 维度 | 评估 |\n"
        content += f"|------|------|\n"
        content += f"| 工作量 | {proposal.get('effort', 'medium')} |\n"
        content += f"| 影响程度 | {proposal.get('impact', 'medium')} |\n"
        content += f"| 优先级 | {proposal.get('priority', 'P2')} |\n"
        content += f"| 需要审批 | {'是' if proposal.get('requires_approval', True) else '否'} |\n"
        content += f"| 自动部署 | {'否' if not proposal.get('auto_apply', False) else '是'} |\n"
        content += "\n"
        
        content += "---\n\n"
        content += "*🤖 本提案由 Architect 进化导师自动生成*  \n"
        content += "*⚠️ 请人工审核后确认是否实施*\n"
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    async def send_notification(self):
        """发送提案通知"""
        if not self.proposals:
            print("ℹ️ 无提案需要通知")
            return
        
        print("📤 正在发送通知...")
        
        # 构建摘要消息
        p0_count = sum(1 for p in self.proposals if p.get('priority') == 'P0')
        p1_count = sum(1 for p in self.proposals if p.get('priority') == 'P1')
        
        message = f"""🏗️ **Architect 进化报告** ({self.today})

📊 **提案汇总**
- 总计: {len(self.proposals)} 个优化提案
- P0-紧急: {p0_count} 个
- P1-重要: {p1_count} 个

📋 **高优先级提案**
"""
        
        for p in self.proposals[:3]:  # 只显示前3个
            icon = "🚨" if p.get('priority') == 'P0' else "🔶" if p.get('priority') == 'P1' else "🔹"
            message += f"{icon} **{p['title']}** [{p.get('priority', 'P2')}]\n"
            message += f"   问题: {p.get('problem', 'N/A')[:50]}...\n\n"
        
        message += f"""
📁 **查看详情**
所有提案已保存至: `metrics/proposals/{self.today}/`
- summary.json - 汇总信息
- *.md - 详细提案文档

💡 **下一步行动**
请查看提案详情，确认后可手动实施或等待自动部署功能上线。
"""
        
        print(message)
        
        # 实际发送message（后续可启用）
        # await message({"action": "send", "message": message})
    
    def save_learning_notes(self):
        """保存学习笔记"""
        notes_path = DATA_DIR / "daily_notes"
        notes_path.mkdir(exist_ok=True)
        
        note_file = notes_path / f"{self.today}.md"
        
        content = f"""# Architect 学习笔记 - {self.today}

## 系统状态
- 分析Agent数: {len(self.overseer_report.get('agents', {})) if self.overseer_report else 0}
- 识别缺口数: {len(self.gaps)}
- 生成提案数: {len(self.proposals)}

## 识别的缺口
"""
        
        for gap in self.gaps:
            content += f"- [{gap['severity']}] {gap['type']}: {gap.get('agent') or gap.get('capability')}\n"
        
        content += "\n## 生成的提案\n\n"
        for p in self.proposals:
            content += f"- [{p.get('priority', 'P2')}] {p['title']} ({p['type']})\n"
        
        content += "\n## 学到的知识\n\n"
        content += "_待整理_\n"
        
        with open(note_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 学习笔记已保存: {note_file}")
    
    async def run(self):
        """执行完整进化流程"""
        print(f"\n{'='*60}")
        print(f"🏗️ Architect 进化导师 v1.0")
        print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        try:
            # 1. 加载Overseer报告
            if not self.load_overseer_report():
                print("❌ 无法继续，缺少监控数据")
                return {"status": "error", "error": "No overseer report found"}
            
            # 2. 识别缺口
            self.identify_gaps()
            
            # 3. 搜索解决方案（并行）
            if self.gaps:
                print("\n🔍 正在搜索解决方案...")
                for gap in self.gaps:
                    results = await self.search_solutions(gap)
                    gap["search_results"] = results
            
            # 4. 生成提案
            if self.gaps:
                self.generate_proposals()
            
            # 5. 保存提案
            if self.proposals:
                self.save_proposals()
                await self.send_notification()
            else:
                print("ℹ️ 今日无提案生成（系统状态良好）")
            
            # 6. 保存学习笔记
            self.save_learning_notes()
            
            # 7. 记录执行日志
            execution_log = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "gaps_identified": len(self.gaps),
                "proposals_generated": len(self.proposals),
                "by_priority": {
                    "P0": sum(1 for p in self.proposals if p.get("priority") == "P0"),
                    "P1": sum(1 for p in self.proposals if p.get("priority") == "P1"),
                    "P2": sum(1 for p in self.proposals if p.get("priority") not in ["P0", "P1"])
                }
            }
            
            log_path = DATA_DIR / "execution.log"
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(execution_log) + '\n')
            
            print(f"\n{'='*60}")
            print(f"✅ Architect 执行完成")
            print(f"🔍 识别 {len(self.gaps)} 个缺口，生成 {len(self.proposals)} 个提案")
            print(f"📁 提案目录: metrics/proposals/{self.today}/")
            print(f"{'='*60}\n")
            
            return {
                "status": "success",
                "gaps": len(self.gaps),
                "proposals": len(self.proposals),
                "proposals_dir": str(PROPOSALS_DIR / self.today)
            }
            
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}


async def main():
    """入口函数"""
    architect = Architect()
    result = await architect.run()
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result["status"] == "success" else 1)
