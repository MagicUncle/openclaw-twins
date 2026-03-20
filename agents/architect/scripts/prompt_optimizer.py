#!/usr/bin/env python3
"""
PromptOptimizer - 自动Prompt优化器 v2.0
基于A/B测试和效果反馈自动迭代优化Prompt
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from ab_test_framework import ABTestManager, TestType

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
PROMPTS_DIR = WORKSPACE / "agents" / "architect" / "data" / "prompts"
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


class PromptOptimizer:
    """Prompt自动优化器"""
    
    # 优化策略模板
    OPTIMIZATION_STRATEGIES = {
        "few_shot": {
            "name": "添加Few-shot示例",
            "description": "在Prompt中添加输入输出示例",
            "template": "\n\n示例:\n输入: {example_input}\n输出: {example_output}\n\n现在请处理以下输入:\n{original_prompt}"
        },
        "chain_of_thought": {
            "name": "思维链提示",
            "description": "引导模型逐步思考",
            "template": "\n\n请按以下步骤思考:\n1. 分析问题\n2. 制定方案\n3. 执行并验证\n4. 输出结果\n\n{original_prompt}"
        },
        "role_definition": {
            "name": "角色定义",
            "description": "明确指定模型角色",
            "template": "你是一位专业的{role}。{original_prompt}"
        },
        "output_format": {
            "name": "输出格式约束",
            "description": "指定输出格式要求",
            "template": "\n\n输出要求:\n- 使用结构化格式\n- 包含关键字段: {fields}\n- 使用Markdown语法\n\n{original_prompt}"
        },
        "constraints": {
            "name": "添加约束条件",
            "description": "明确约束和限制",
            "template": "\n\n约束条件:\n- {constraints}\n\n{original_prompt}"
        },
        "context_enrichment": {
            "name": "上下文增强",
            "description": "添加背景信息",
            "template": "背景信息: {context}\n\n{original_prompt}"
        }
    }
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.prompts_file = PROMPTS_DIR / f"{agent_name}_prompts.json"
        self.prompt_history = self._load_history()
        self.ab_manager = ABTestManager()
    
    def _load_history(self) -> List[Dict]:
        """加载Prompt历史"""
        if self.prompts_file.exists():
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """保存Prompt历史"""
        with open(self.prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.prompt_history, f, indent=2, ensure_ascii=False)
    
    def analyze_current_prompt(self, current_prompt: str) -> Dict:
        """分析当前Prompt的问题"""
        issues = []
        suggestions = []
        
        # 检查长度
        if len(current_prompt) < 50:
            issues.append("Prompt过短，缺乏足够上下文")
            suggestions.append("context_enrichment")
        elif len(current_prompt) > 2000:
            issues.append("Prompt过长，可能导致Token浪费")
            suggestions.append("conciseness")
        
        # 检查结构
        if "\n" not in current_prompt:
            issues.append("缺乏结构化，可读性差")
            suggestions.append("output_format")
        
        # 检查示例
        if "示例" not in current_prompt and "example" not in current_prompt.lower():
            issues.append("缺少Few-shot示例")
            suggestions.append("few_shot")
        
        # 检查角色定义
        role_patterns = ["你是", "作为", "扮演", "role:", "you are"]
        if not any(p in current_prompt.lower() for p in role_patterns):
            issues.append("缺少明确的角色定义")
            suggestions.append("role_definition")
        
        # 检查思维链
        thought_patterns = ["步骤", "思考", "分析", "step", "think"]
        if not any(p in current_prompt.lower() for p in thought_patterns):
            issues.append("缺少思维引导")
            suggestions.append("chain_of_thought")
        
        # 检查输出格式
        format_patterns = ["输出", "返回", "格式", "output", "format"]
        if not any(p in current_prompt.lower() for p in format_patterns):
            issues.append("缺少输出格式说明")
            suggestions.append("output_format")
        
        return {
            "issues": issues,
            "suggestions": list(set(suggestions)),
            "length": len(current_prompt),
            "lines": current_prompt.count('\n') + 1,
            "score": max(0, 100 - len(issues) * 15)
        }
    
    def generate_optimized_prompts(self, current_prompt: str, strategies: List[str] = None) -> List[Dict]:
        """生成优化的Prompt变体"""
        if strategies is None:
            analysis = self.analyze_current_prompt(current_prompt)
            strategies = analysis["suggestions"]
        
        variants = []
        
        # 基础Prompt
        variants.append({
            "name": "baseline",
            "prompt": current_prompt,
            "changes": "原始版本"
        })
        
        # 应用各种优化策略
        for strategy_key in strategies:
            if strategy_key in self.OPTIMIZATION_STRATEGIES:
                strategy = self.OPTIMIZATION_STRATEGIES[strategy_key]
                
                # 生成变体
                optimized = self._apply_strategy(
                    current_prompt, 
                    strategy_key, 
                    strategy["template"]
                )
                
                variants.append({
                    "name": f"optimized_{strategy_key}",
                    "prompt": optimized,
                    "changes": strategy["name"],
                    "strategy": strategy_key
                })
        
        # 生成组合优化版本
        if len(strategies) >= 2:
            combined = current_prompt
            changes = []
            
            for strategy_key in strategies[:2]:  # 最多组合2个
                strategy = self.OPTIMIZATION_STRATEGIES[strategy_key]
                combined = self._apply_strategy(combined, strategy_key, strategy["template"])
                changes.append(strategy["name"])
            
            variants.append({
                "name": "optimized_combined",
                "prompt": combined,
                "changes": " + ".join(changes),
                "strategy": "combined"
            })
        
        return variants
    
    def _apply_strategy(self, prompt: str, strategy: str, template: str) -> str:
        """应用优化策略"""
        if strategy == "few_shot":
            return template.format(
                example_input="示例输入",
                example_output="示例输出",
                original_prompt=prompt
            )
        elif strategy == "role_definition":
            return template.format(
                role="专业助手",
                original_prompt=prompt
            )
        elif strategy == "output_format":
            return template.format(
                fields="result, status, message",
                original_prompt=prompt
            )
        elif strategy == "constraints":
            return template.format(
                constraints="保持简洁，避免冗余",
                original_prompt=prompt
            )
        elif strategy == "context_enrichment":
            return template.format(
                context="这是任务的背景信息...",
                original_prompt=prompt
            )
        else:
            return template.format(original_prompt=prompt)
    
    def create_optimization_test(self, current_prompt: str, test_duration_days: int = 3) -> Optional[str]:
        """创建Prompt优化A/B测试"""
        # 分析并生成变体
        analysis = self.analyze_current_prompt(current_prompt)
        
        if analysis["score"] >= 90:
            print(f"✅ {self.agent_name} 的Prompt质量已很好 (得分: {analysis['score']})，无需优化")
            return None
        
        variants = self.generate_optimized_prompts(current_prompt, analysis["suggestions"])
        
        if len(variants) < 2:
            print(f"⚠️ 无法生成足够的变体")
            return None
        
        # 创建A/B测试
        test = self.ab_manager.create_test(
            name=f"{self.agent_name}_prompt_optimization",
            test_type=TestType.PROMPT,
            target_agent=self.agent_name,
            description=f"自动优化{self.agent_name}的Prompt，当前得分: {analysis['score']}"
        )
        
        # 添加变体
        traffic_per_variant = 100.0 / len(variants)
        for variant in variants:
            test.add_variant(
                name=variant["name"],
                content={
                    "prompt": variant["prompt"],
                    "changes": variant.get("changes", "")
                },
                traffic_percentage=traffic_per_variant
            )
        
        # 保存到历史
        self.prompt_history.append({
            "timestamp": datetime.now().isoformat(),
            "test_id": test.test_id,
            "original_prompt": current_prompt,
            "variants": variants,
            "analysis": analysis
        })
        self._save_history()
        
        # 启动测试
        test.start()
        
        print(f"✅ 创建Prompt优化测试: {test.test_id}")
        print(f"   原始Prompt得分: {analysis['score']}")
        print(f"   生成变体数: {len(variants)}")
        print(f"   测试时长: {test_duration_days}天")
        
        return test.test_id
    
    def get_optimization_report(self, test_id: str) -> Optional[Dict]:
        """获取优化报告"""
        test = self.ab_manager.get_test(test_id)
        if not test:
            return None
        
        results = test.get_results()
        
        # 找到对应的历史记录
        history_entry = None
        for h in self.prompt_history:
            if h.get("test_id") == test_id:
                history_entry = h
                break
        
        if not history_entry:
            return results
        
        # 生成详细报告
        report = {
            **results,
            "optimization_details": {
                "original_score": history_entry["analysis"]["score"],
                "original_issues": history_entry["analysis"]["issues"],
                "optimization_strategies": [v.get("strategy") for v in history_entry["variants"] if v.get("strategy")]
            }
        }
        
        # 计算改进
        if results["variants"]:
            best_variant = results["variants"][0]
            baseline = next((v for v in results["variants"] if v["name"] == "baseline"), None)
            
            if baseline and best_variant["name"] != "baseline":
                improvement = (
                    (best_variant["success_rate"] / baseline["success_rate"] - 1) * 100
                    if baseline["success_rate"] > 0 else 0
                )
                report["optimization_details"]["improvement_percentage"] = f"{improvement:.1f}%"
        
        return report
    
    def apply_winner(self, test_id: str) -> bool:
        """应用胜出Prompt"""
        test = self.ab_manager.get_test(test_id)
        if not test or not test.winner_variant_id:
            print("❌ 测试未完成或无胜出者")
            return False
        
        # 获取胜出变体
        winner = next(
            (v for v in test.variants if v.id == test.winner_variant_id),
            None
        )
        
        if not winner:
            print("❌ 未找到胜出变体")
            return False
        
        # 保存胜出Prompt
        winner_file = PROMPTS_DIR / f"{self.agent_name}_winner.json"
        with open(winner_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_id": test_id,
                "applied_at": datetime.now().isoformat(),
                "winner_variant": winner.name,
                "prompt": winner.content["prompt"],
                "changes": winner.content.get("changes", "")
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已应用胜出Prompt: {winner.name}")
        print(f"   保存到: {winner_file}")
        
        return True


def test_prompt_optimizer():
    """测试Prompt优化器"""
    print(f"\n{'='*60}")
    print("📝 Prompt自动优化器 v2.0 测试")
    print(f"{'='*60}\n")
    
    # 一个需要优化的Prompt示例
    current_prompt = """
处理用户请求。
"""
    
    optimizer = PromptOptimizer("test_agent")
    
    # 分析当前Prompt
    print("🔍 分析当前Prompt...")
    analysis = optimizer.analyze_current_prompt(current_prompt)
    print(f"   得分: {analysis['score']}/100")
    print(f"   问题: {len(analysis['issues'])}个")
    for issue in analysis["issues"]:
        print(f"      - {issue}")
    print(f"   建议策略: {', '.join(analysis['suggestions'])}")
    
    # 生成优化版本
    print("\n✨ 生成优化版本...")
    variants = optimizer.generate_optimized_prompts(current_prompt)
    print(f"   生成 {len(variants)} 个变体")
    for v in variants:
        print(f"      - {v['name']}: {v['changes']}")
    
    # 创建A/B测试
    print("\n🧪 创建A/B测试...")
    test_id = optimizer.create_optimization_test(current_prompt, test_duration_days=3)
    
    if test_id:
        print(f"   测试ID: {test_id}")
        
        # 获取测试
        test = optimizer.ab_manager.get_test(test_id)
        
        # 模拟一些调用
        print("\n📊 模拟测试数据...")
        for i in range(50):
            variant = test.assign_variant(f"user_{i}")
            if variant:
                test.record_event(variant.id, "impression", {})
                
                # 优化版本有更好的成功率
                if "optimized" in variant.name:
                    success = __import__('random').random() < 0.88
                else:
                    success = __import__('random').random() < 0.72
                
                if success:
                    test.record_event(variant.id, "success", {})
                else:
                    test.record_event(variant.id, "failure", {})
        
        # 停止测试并选择胜出者
        results = test.get_results()
        winner_id = results["variants"][0]["id"] if results["variants"] else None
        test.stop(winner_variant_id=winner_id)
        
        # 生成报告
        print("\n📈 优化报告:")
        report = optimizer.get_optimization_report(test_id)
        if report:
            print(f"   原始得分: {report['optimization_details']['original_score']}")
            if 'improvement_percentage' in report['optimization_details']:
                print(f"   改进: {report['optimization_details']['improvement_percentage']}")
            print(f"   推荐: {report['recommendation']['action']}")
        
        # 应用胜出者
        print("\n🎯 应用胜出Prompt...")
        optimizer.apply_winner(test_id)


if __name__ == "__main__":
    test_prompt_optimizer()
