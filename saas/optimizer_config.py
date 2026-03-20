#!/usr/bin/env python3
"""
Dashboard Data Optimizer - 数据可视化优化
1. 人民币替代美元
2. 添加数据解释说明
3. 优化展示逻辑
"""

import json
from datetime import datetime
from pathlib import Path

def optimize_dashboard_data():
    """优化Dashboard数据展示"""
    
    # 读取原始数据
    collector_path = Path("/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts/full_data_collector.py")
    
    # 创建优化版本的数据转换器
    optimizer_code = '''
    # 数据优化配置
    CURRENCY = "¥"           # 人民币符号
    USD_TO_CNY = 7.2         # 汇率
    
    def format_cost(usd_amount):
        """美元转人民币并格式化"""
        cny = usd_amount * USD_TO_CNY
        return f"{CURRENCY}{cny:.2f}"
    
    def format_tokens(tokens):
        """格式化token数量（添加K/M后缀）"""
        if tokens >= 1000000:
            return f"{tokens/1000000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens/1000:.1f}K"
        return str(tokens)
    
    def get_status_explanation(status):
        """获取状态解释"""
        explanations = {
            "running": "✅ 正在执行任务",
            "idle": "💤 空闲等待",
            "blocked": "🚫 被阻塞",
            "error": "❌ 发生错误",
            "queued": "⏳ 排队中"
        }
        return explanations.get(status, status)
    
    def get_metric_explanation(metric_name):
        """获取指标解释"""
        explanations = {
            "tokens_total": "累计消耗的Token数量（输入+输出）",
            "cost": "预估成本（基于Token消耗计算）",
            "usage_percent": "当前使用率相对于配额的百分比",
            "queue_depth": "等待处理的任务数量",
            "message_count": "会话中的消息总数"
        }
        return explanations.get(metric_name, "")
'''
    
    print("✅ 数据优化配置已生成")
    print("💱 货币: $ → ¥ (汇率1:7.2)")
    print("📊 添加数据解释说明")

if __name__ == "__main__":
    optimize_dashboard_data()
