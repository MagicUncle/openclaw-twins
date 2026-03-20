#!/usr/bin/env python3
"""
ABTestFramework - A/B测试框架 v2.0
支持Prompt、策略、配置的对比实验
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
DATA_DIR = WORKSPACE / "agents" / "architect" / "data" / "ab_tests"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class TestStatus(Enum):
    """测试状态"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TestType(Enum):
    """测试类型"""
    PROMPT = "prompt"
    STRATEGY = "strategy"
    CONFIG = "config"
    MODEL = "model"


@dataclass
class Variant:
    """测试变体"""
    id: str
    name: str
    content: Dict[str, Any]
    traffic_percentage: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TestMetrics:
    """测试指标"""
    variant_id: str
    impressions: int = 0
    successes: int = 0
    failures: int = 0
    total_tokens: int = 0
    total_duration_ms: int = 0
    user_ratings: List[int] = None
    
    def __post_init__(self):
        if self.user_ratings is None:
            self.user_ratings = []
    
    @property
    def success_rate(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.successes / self.impressions
    
    @property
    def avg_tokens(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.total_tokens / self.impressions
    
    @property
    def avg_duration_ms(self) -> float:
        if self.impressions == 0:
            return 0.0
        return self.total_duration_ms / self.impressions
    
    @property
    def avg_rating(self) -> float:
        if not self.user_ratings:
            return 0.0
        return sum(self.user_ratings) / len(self.user_ratings)
    
    def to_dict(self) -> Dict:
        return {
            "variant_id": self.variant_id,
            "impressions": self.impressions,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "avg_tokens": self.avg_tokens,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "user_ratings": self.user_ratings,
            "avg_rating": self.avg_rating
        }


class ABTest:
    """A/B测试"""
    
    def __init__(self, test_id: str):
        self.test_id = test_id
        self.test_file = DATA_DIR / f"{test_id}.json"
        
        # 加载或创建
        if self.test_file.exists():
            self._load()
        else:
            self._create_new()
    
    def _create_new(self):
        """创建新测试"""
        self.name = ""
        self.description = ""
        self.test_type = TestType.PROMPT
        self.target_agent = ""
        self.status = TestStatus.DRAFT
        self.variants: List[Variant] = []
        self.metrics: Dict[str, TestMetrics] = {}
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.winner_variant_id = None
        self.confidence_level = 0.95
        self.min_sample_size = 100
        self.max_duration_days = 7
    
    def _load(self):
        """从文件加载"""
        with open(self.test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.name = data.get('name', '')
        self.description = data.get('description', '')
        self.test_type = TestType(data.get('test_type', 'prompt'))
        self.target_agent = data.get('target_agent', '')
        self.status = TestStatus(data.get('status', 'draft'))
        self.variants = [Variant(**v) for v in data.get('variants', [])]
        
        # 加载metrics时只加载原始数据字段
        self.metrics = {}
        for k, v in data.get('metrics', {}).items():
            # 只保留原始字段，过滤掉计算字段
            metric_data = {
                "variant_id": v.get("variant_id", k),
                "impressions": v.get("impressions", 0),
                "successes": v.get("successes", 0),
                "failures": v.get("failures", 0),
                "total_tokens": v.get("total_tokens", 0),
                "total_duration_ms": v.get("total_duration_ms", 0),
                "user_ratings": v.get("user_ratings", [])
            }
            self.metrics[k] = TestMetrics(**metric_data)
        
        self.created_at = data.get('created_at')
        self.started_at = data.get('started_at')
        self.completed_at = data.get('completed_at')
        self.winner_variant_id = data.get('winner_variant_id')
        self.confidence_level = data.get('confidence_level', 0.95)
        self.min_sample_size = data.get('min_sample_size', 100)
        self.max_duration_days = data.get('max_duration_days', 7)
    
    def save(self):
        """保存到文件"""
        data = {
            "test_id": self.test_id,
            "name": self.name,
            "description": self.description,
            "test_type": self.test_type.value,
            "target_agent": self.target_agent,
            "status": self.status.value,
            "variants": [v.to_dict() for v in self.variants],
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "winner_variant_id": self.winner_variant_id,
            "confidence_level": self.confidence_level,
            "min_sample_size": self.min_sample_size,
            "max_duration_days": self.max_duration_days
        }
        
        with open(self.test_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_variant(self, name: str, content: Dict, traffic_percentage: float = 50.0) -> str:
        """添加变体"""
        variant_id = f"variant_{len(self.variants)}"
        
        variant = Variant(
            id=variant_id,
            name=name,
            content=content,
            traffic_percentage=traffic_percentage
        )
        
        self.variants.append(variant)
        self.metrics[variant_id] = TestMetrics(variant_id=variant_id)
        
        return variant_id
    
    def assign_variant(self, user_id: Optional[str] = None) -> Optional[Variant]:
        """为用户分配变体"""
        if self.status != TestStatus.RUNNING:
            return None
        
        # 基于用户ID哈希分配（保证同一用户始终分配到相同变体）
        if user_id:
            hash_val = hash(user_id) % 100
            cumulative = 0
            for variant in self.variants:
                cumulative += variant.traffic_percentage
                if hash_val < cumulative:
                    return variant
        
        # 随机分配
        return random.choices(
            self.variants,
            weights=[v.traffic_percentage for v in self.variants]
        )[0]
    
    def record_event(self, variant_id: str, event_type: str, data: Dict):
        """记录事件"""
        if variant_id not in self.metrics:
            return
        
        metrics = self.metrics[variant_id]
        
        if event_type == "impression":
            metrics.impressions += 1
        elif event_type == "success":
            metrics.successes += 1
        elif event_type == "failure":
            metrics.failures += 1
        elif event_type == "tokens":
            metrics.total_tokens += data.get("tokens", 0)
        elif event_type == "duration":
            metrics.total_duration_ms += data.get("duration_ms", 0)
        elif event_type == "rating":
            metrics.user_ratings.append(data.get("rating", 0))
    
    def start(self):
        """启动测试"""
        if len(self.variants) < 2:
            raise ValueError("至少需要2个变体")
        
        # 检查流量分配是否100%
        total_traffic = sum(v.traffic_percentage for v in self.variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"流量分配总和必须是100%，当前为{total_traffic}%")
        
        self.status = TestStatus.RUNNING
        self.started_at = datetime.now().isoformat()
        self.save()
    
    def pause(self):
        """暂停测试"""
        self.status = TestStatus.PAUSED
        self.save()
    
    def resume(self):
        """恢复测试"""
        self.status = TestStatus.RUNNING
        self.save()
    
    def stop(self, winner_variant_id: Optional[str] = None):
        """停止测试"""
        self.status = TestStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
        self.winner_variant_id = winner_variant_id
        self.save()
    
    def get_results(self) -> Dict:
        """获取测试结果"""
        results = {
            "test_id": self.test_id,
            "name": self.name,
            "status": self.status.value,
            "total_impressions": sum(m.impressions for m in self.metrics.values()),
            "variants": [],
            "recommendation": None
        }
        
        # 排序变体
        sorted_variants = sorted(
            self.variants,
            key=lambda v: self.metrics[v.id].success_rate,
            reverse=True
        )
        
        for variant in sorted_variants:
            metrics = self.metrics[variant.id]
            results["variants"].append({
                "id": variant.id,
                "name": variant.name,
                "traffic_percentage": variant.traffic_percentage,
                **metrics.to_dict()
            })
        
        # 生成推荐
        if results["variants"]:
            best = results["variants"][0]
            worst = results["variants"][-1]
            
            if best["success_rate"] > worst["success_rate"] * 1.1:  # 10%提升
                results["recommendation"] = {
                    "winner": best["name"],
                    "confidence": "high" if best["impressions"] > self.min_sample_size else "medium",
                    "improvement": f"{((best['success_rate'] / worst['success_rate'] - 1) * 100):.1f}%",
                    "action": "建议全量部署"
                }
            else:
                results["recommendation"] = {
                    "winner": None,
                    "confidence": "low",
                    "action": "差异不显著，建议延长测试或重新设计"
                }
        
        return results
    
    def should_stop_early(self) -> Tuple[bool, str]:
        """检查是否应该提前停止"""
        # 检查最小样本量
        for metrics in self.metrics.values():
            if metrics.impressions < self.min_sample_size:
                return False, "样本量不足"
        
        # 检查显著差异
        results = self.get_results()
        variants = results["variants"]
        
        if len(variants) >= 2:
            best_rate = variants[0]["success_rate"]
            worst_rate = variants[-1]["success_rate"]
            
            # 如果最佳和最差差异巨大
            if best_rate > worst_rate * 1.2:  # 20%差异
                return True, "已出现显著差异"
        
        # 检查最大时长
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            if datetime.now() - start > timedelta(days=self.max_duration_days):
                return True, "达到最大测试时长"
        
        return False, "继续测试"


class ABTestManager:
    """A/B测试管理器"""
    
    def __init__(self):
        self.active_tests: Dict[str, ABTest] = {}
        self._load_all_tests()
    
    def _load_all_tests(self):
        """加载所有测试"""
        for test_file in DATA_DIR.glob("*.json"):
            test_id = test_file.stem
            self.active_tests[test_id] = ABTest(test_id)
    
    def create_test(self, 
                   name: str,
                   test_type: TestType,
                   target_agent: str,
                   description: str = "") -> ABTest:
        """创建新测试"""
        test_id = f"ab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        test = ABTest(test_id)
        test.name = name
        test.test_type = test_type
        test.target_agent = target_agent
        test.description = description
        test.save()
        
        self.active_tests[test_id] = test
        return test
    
    def get_test(self, test_id: str) -> Optional[ABTest]:
        """获取测试"""
        return self.active_tests.get(test_id)
    
    def list_tests(self, status: Optional[TestStatus] = None) -> List[Dict]:
        """列出测试"""
        tests = []
        
        for test in self.active_tests.values():
            if status and test.status != status:
                continue
            
            tests.append({
                "test_id": test.test_id,
                "name": test.name,
                "type": test.test_type.value,
                "target": test.target_agent,
                "status": test.status.value,
                "variants": len(test.variants),
                "created_at": test.created_at
            })
        
        return sorted(tests, key=lambda x: x["created_at"], reverse=True)
    
    def check_all_tests(self):
        """检查所有测试状态"""
        for test in self.active_tests.values():
            if test.status == TestStatus.RUNNING:
                should_stop, reason = test.should_stop_early()
                if should_stop:
                    print(f"⚠️ 测试 {test.name} 建议停止: {reason}")
                    results = test.get_results()
                    winner = results["recommendation"].get("winner")
                    test.stop(winner_variant_id=winner)


def test_ab_framework():
    """测试A/B测试框架"""
    print(f"\n{'='*60}")
    print("🧪 A/B测试框架 v2.0 测试")
    print(f"{'='*60}\n")
    
    # 创建测试
    manager = ABTestManager()
    
    test = manager.create_test(
        name="wenyuan_prompt_optimization",
        test_type=TestType.PROMPT,
        target_agent="wenyuan",
        description="测试不同Prompt模板对wenyuan成功率的影响"
    )
    print(f"✅ 创建测试: {test.test_id}")
    
    # 添加变体
    test.add_variant(
        name="baseline",
        content={"prompt": "原始Prompt"},
        traffic_percentage=50.0
    )
    test.add_variant(
        name="optimized",
        content={"prompt": "优化后的Prompt，包含Few-shot示例"},
        traffic_percentage=50.0
    )
    print(f"✅ 添加2个变体")
    
    # 启动测试
    test.start()
    print(f"✅ 测试已启动")
    
    # 模拟一些事件
    for i in range(100):
        variant = test.assign_variant(f"user_{i}")
        if variant:
            test.record_event(variant.id, "impression", {})
            
            # 模拟成功率差异
            if variant.name == "optimized":
                success = random.random() < 0.9  # 90%成功率
            else:
                success = random.random() < 0.75  # 75%成功率
            
            if success:
                test.record_event(variant.id, "success", {})
            else:
                test.record_event(variant.id, "failure", {})
            
            test.record_event(variant.id, "tokens", {"tokens": random.randint(500, 1500)})
    
    print(f"✅ 模拟100次调用")
    
    # 获取结果
    results = test.get_results()
    print(f"\n📊 测试结果:")
    for v in results["variants"]:
        print(f"  {v['name']}: 调用{v['impressions']}次, 成功率{v['success_rate']:.1%}")
    
    if results["recommendation"]:
        print(f"\n💡 推荐: {results['recommendation']['action']}")
        if results['recommendation'].get('winner'):
            print(f"   胜出者: {results['recommendation']['winner']}")
            print(f"   提升: {results['recommendation']['improvement']}")
    
    # 停止测试
    test.stop(winner_variant_id=results["variants"][0]["id"])
    print(f"\n✅ 测试已完成")


if __name__ == "__main__":
    test_ab_framework()
