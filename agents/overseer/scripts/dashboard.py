#!/usr/bin/env python3
"""
Dashboard - 监控看板生成器 v1.0
生成可视化监控看板
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
METRICS_DIR = WORKSPACE / "metrics"
DAILY_DIR = METRICS_DIR / "daily"
REPORTS_DIR = METRICS_DIR / "reports"
DASHBOARD_DIR = METRICS_DIR / "dashboard"

DASHBOARD_DIR.mkdir(exist_ok=True)


class Dashboard:
    """监控看板生成器"""
    
    def load_recent_reports(self, days: int = 7) -> List[Dict]:
        """加载最近N天的报告"""
        reports = []
        today = datetime.now()
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            report_path = DAILY_DIR / f"{date}.json"
            
            if report_path.exists():
                with open(report_path, 'r', encoding='utf-8') as f:
                    report = json.load(f)
                    report['_date'] = date
                    reports.append(report)
        
        return reports
    
    def calculate_trends(self, reports: List[Dict]) -> Dict:
        """计算趋势"""
        if len(reports) < 2:
            return {}
        
        # 按日期排序
        reports.sort(key=lambda r: r['_date'])
        
        trends = {
            "total_calls": {
                "latest": reports[-1]['summary']['total_calls'],
                "previous": reports[-2]['summary']['total_calls'],
                "change": reports[-1]['summary']['total_calls'] - reports[-2]['summary']['total_calls']
            },
            "total_tokens": {
                "latest": reports[-1]['summary']['total_tokens'],
                "previous": reports[-2]['summary']['total_tokens'],
                "change": reports[-1]['summary']['total_tokens'] - reports[-2]['summary']['total_tokens']
            },
            "avg_success_rate": {
                "latest": reports[-1]['summary']['avg_success_rate'],
                "previous": reports[-2]['summary']['avg_success_rate'],
                "change": reports[-1]['summary']['avg_success_rate'] - reports[-2]['summary']['avg_success_rate']
            }
        }
        
        return trends
    
    def generate_html_dashboard(self) -> Path:
        """生成HTML看板"""
        reports = self.load_recent_reports(7)
        
        if not reports:
            print("⚠️ 无历史报告数据")
            return None
        
        latest = reports[-1]
        trends = self.calculate_trends(reports)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Agent OS - 监控看板</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .header p {{
            opacity: 0.9;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .metric-card h3 {{
            color: #666;
            font-size: 0.875rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }}
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #333;
        }}
        .metric-change {{
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }}
        .metric-change.positive {{
            color: #10b981;
        }}
        .metric-change.negative {{
            color: #ef4444;
        }}
        .section {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-bottom: 1rem;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            font-weight: 600;
            color: #666;
            font-size: 0.875rem;
        }}
        .grade-A {{ color: #10b981; font-weight: bold; }}
        .grade-B {{ color: #f59e0b; font-weight: bold; }}
        .grade-C {{ color: #ef4444; font-weight: bold; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-P0 {{ background: #fee2e2; color: #991b1b; }}
        .badge-P1 {{ background: #fef3c7; color: #92400e; }}
        .badge-P2 {{ background: #dbeafe; color: #1e40af; }}
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            font-size: 0.875rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 OpenClaw Agent OS 监控看板</h1>
        <p>实时监控系统健康状态与Agent效能</p>
        <p style="margin-top: 0.5rem; font-size: 0.875rem;">更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    
    <div class="container">
        <!-- 核心指标 -->
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>活跃Agent</h3>
                <div class="metric-value">{latest['summary']['total_agents']}</div>
            </div>
            <div class="metric-card">
                <h3>今日调用次数</h3>
                <div class="metric-value">{latest['summary']['total_calls']}</div>
                {f'<div class="metric-change {"positive" if trends.get("total_calls", {}).get("change", 0) >= 0 else "negative"}">{trends["total_calls"]["change"]:+d} vs 昨日</div>' if trends else ''}
            </div>
            <div class="metric-card">
                <h3>Token消耗</h3>
                <div class="metric-value">{latest['summary']['total_tokens']:,}</div>
                {f'<div class="metric-change {"negative" if trends.get("total_tokens", {}).get("change", 0) >= 0 else "positive"}">{trends["total_tokens"]["change"]:+d} vs 昨日</div>' if trends else ''}
            </div>
            <div class="metric-card">
                <h3>平均成功率</h3>
                <div class="metric-value">{latest['summary']['avg_success_rate']:.1%}</div>
                {f'<div class="metric-change {"positive" if trends.get("avg_success_rate", {}).get("change", 0) >= 0 else "negative"}">{trends["avg_success_rate"]["change"]:+.1%} vs 昨日</div>' if trends else ''}
            </div>
        </div>
        
        <!-- Agent排名 -->
        <div class="section">
            <h2>🏆 Agent效能排名</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>Agent</th>
                        <th>效能分</th>
                        <th>成功率</th>
                        <th>等级</th>
                        <th>调用次数</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # 添加排名数据
        ranking = latest.get('ranking', [])
        for i, item in enumerate(ranking[:10], 1):
            grade_class = f"grade-{item.get('grade', 'C')}"
            html += f"""
                    <tr>
                        <td>{"🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else i}</td>
                        <td><strong>{item['name']}</strong></td>
                        <td>{item['efficiency_score']}</td>
                        <td>{item['success_rate']:.1%}</td>
                        <td class="{grade_class}">{item['grade']}</td>
                        <td>{item['calls']}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        
        # 添加洞察
        insights = latest.get('insights', [])
        if insights:
            html += """
        <!-- 系统洞察 -->
        <div class="section">
            <h2>💡 系统洞察</h2>
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>问题</th>
                        <th>建议</th>
                    </tr>
                </thead>
                <tbody>
"""
            for insight in insights:
                badge_class = f"badge-{insight.get('level', 'P2')}"
                html += f"""
                    <tr>
                        <td><span class="badge {badge_class}">{insight.get('level', 'P2')}</span></td>
                        <td>{insight.get('title', '')}</td>
                        <td>{insight.get('suggestion', '')}</td>
                    </tr>
"""
            html += """
                </tbody>
            </table>
        </div>
"""
        
        html += f"""
    </div>
    
    <div class="footer">
        <p>🤖 OpenClaw Agent OS v1.0 | 📊 数据由 Overseer 监控优化师自动生成</p>
        <p>下次更新: {datetime.now().strftime("%Y-%m-%d")} 18:00</p>
    </div>
</body>
</html>
"""
        
        # 保存HTML
        dashboard_path = DASHBOARD_DIR / "index.html"
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ HTML看板已生成: {dashboard_path}")
        return dashboard_path
    
    def run(self):
        """执行看板生成"""
        print("📊 正在生成监控看板...")
        
        dashboard_path = self.generate_html_dashboard()
        
        if dashboard_path:
            print(f"\n🌐 查看看板: file://{dashboard_path}")
            return {"status": "success", "path": str(dashboard_path)}
        else:
            return {"status": "error", "error": "No data available"}


def main():
    dashboard = Dashboard()
    result = dashboard.run()
    return result


if __name__ == "__main__":
    main()
