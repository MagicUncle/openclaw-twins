#!/usr/bin/env python3
"""
Complete Dashboard - 完整数据展示
基于Control Center的完整数据模型，展示所有指标
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts')
from full_data_collector import FullDataCollector

def generate_dashboard_html():
    """生成完整Dashboard HTML"""
    
    # 采集完整数据
    collector = FullDataCollector()
    data = collector.get_full_snapshot()
    
    # 转换为JSON字符串供前端使用
    data_json = json.dumps({
        "generated_at": data.generated_at,
        "sessions": [{
            "session_key": s.session_key,
            "agent_id": s.agent_id,
            "state": s.state.value,
            "tokens_total": s.tokens_in + s.tokens_out,
            "cost": s.cost,
            "message_count": s.message_count,
            "duration_minutes": s.duration_minutes,
            "errors": s.errors,
            "tool_calls": s.tool_calls
        } for s in data.sessions],
        "budget": {
            "total_cost": data.total_estimated_cost,
            "metrics": [{
                "scope_id": b.scope_id,
                "used": b.used,
                "limit": b.limit,
                "usage_percent": b.usage_percent,
                "status": b.status,
                "estimated_cost": b.estimated_cost
            } for b in data.budget_metrics]
        },
        "alerts": [{
            "level": a.level.value,
            "code": a.code,
            "message": a.message,
            "count": a.count
        } for a in data.alerts],
        "summary": {
            "session_count": data.session_count,
            "active_sessions": data.active_sessions,
            "blocked_sessions": data.blocked_sessions,
            "error_sessions": data.error_sessions,
            "pending_approvals": data.pending_approvals,
            "over_budget_count": data.over_budget_count,
            "total_cost": data.total_estimated_cost
        }
    }, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Agent OS - 完整Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background: #f8fafc; }}
        .gradient-bg {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .card {{ background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 2rem; font-weight: 700; }}
        .sidebar {{ background: #1e293b; min-height: 100vh; }}
        .badge {{ display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }}
        .badge-red {{ background: #fee2e2; color: #991b1b; }}
        .badge-yellow {{ background: #fef3c7; color: #92400e; }}
        .badge-green {{ background: #d1fae5; color: #065f46; }}
        .badge-blue {{ background: #dbeafe; color: #1e40af; }}
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const {{ useState, useEffect, useCallback }} = React;
        
        // 初始数据
        const initialData = {data_json};
        
        // 完整Dashboard组件
        function CompleteDashboard() {{
            const [data, setData] = useState(initialData);
            const [lastUpdate, setLastUpdate] = useState(new Date());
            const [heartbeatCount, setHeartbeatCount] = useState(0);
            
            // 心跳机制：每30秒刷新数据
            const heartbeat = useCallback(async () => {{
                try {{
                    const response = await fetch('/api/v1/system/snapshot');
                    if (response.ok) {{
                        const newData = await response.json();
                        setData(newData);
                        setLastUpdate(new Date());
                        setHeartbeatCount(prev => prev + 1);
                        console.log('✅ 心跳刷新成功:', new Date().toLocaleTimeString());
                    }}
                }} catch (error) {{
                    console.log('⚠️ 心跳失败，使用本地数据');
                }}
            }}, []);
            
            useEffect(() => {{
                // 立即执行一次
                heartbeat();
                
                // 设置30秒心跳
                const interval = setInterval(heartbeat, 30000);
                
                return () => clearInterval(interval);
            }}, [heartbeat]);
            
            const summary = data.summary || {{}};
            const sessions = data.sessions || [];
            const budget = data.budget || {{}};
            const alerts = data.alerts || [];
            
            // 按Agent分组session
            const sessionsByAgent = sessions.reduce((acc, s) => {{
                if (!acc[s.agent_id]) acc[s.agent_id] = [];
                acc[s.agent_id].push(s);
                return acc;
            }}, {{}});
            
            return (
                <div className="flex min-h-screen">
                    {/* Sidebar */}}
                    <div className="sidebar w-64 text-white p-6">
                        <h1 className="text-xl font-bold mb-8">OpenClaw Control</h1>
                        <nav className="space-y-2">
                            <div className="px-4 py-2 bg-purple-600 rounded-lg">📊 Dashboard</div>
                            <div className="px-4 py-2 hover:bg-gray-700 rounded-lg">👥 Staff</div>
                            <div className="px-4 py-2 hover:bg-gray-700 rounded-lg">💰 Budget</div>
                            <div className="px-4 py-2 hover:bg-gray-700 rounded-lg">⚠️ Alerts</div>
                        </nav>
                        <div className="absolute bottom-6 left-6 text-sm text-gray-400">
                            <div>心跳次数: {{heartbeatCount}}</div>
                            <div>最后更新: {{lastUpdate.toLocaleTimeString()}}</div>
                        </div>
                    </div>
                    
                    {/* Main Content */}}
                    <div className="flex-1 p-8 overflow-auto">
                        {/* Header */}}
                        <div className="mb-8">
                            <h2 className="text-2xl font-bold">完整系统监控</h2>
                            <p className="text-gray-600">基于Control Center的完整数据模型</p>
                        </div>
                        
                        {/* Summary Cards */}}
                        <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-8">
                            <div className="card p-4">
                                <div className="text-sm text-gray-600">总Sessions</div>
                                <div className="metric-value">{{summary.session_count || 0}}</div>
                            </div>
                            <div className="card p-4 border-l-4 border-green-500">
                                <div className="text-sm text-gray-600">活跃</div>
                                <div className="metric-value text-green-600">{{summary.active_sessions || 0}}</div>
                            </div>
                            <div className="card p-4 border-l-4 border-yellow-500">
                                <div className="text-sm text-gray-600">阻塞</div>
                                <div className="metric-value text-yellow-600">{{summary.blocked_sessions || 0}}</div>
                            </div>
                            <div className="card p-4 border-l-4 border-red-500">
                                <div className="text-sm text-gray-600">错误</div>
                                <div className="metric-value text-red-600">{{summary.error_sessions || 0}}</div>
                            </div>
                            <div className="card p-4 border-l-4 border-orange-500">
                                <div className="text-sm text-gray-600">待审批</div>
                                <div className="metric-value text-orange-600">{{summary.pending_approvals || 0}}</div>
                            </div>
                            <div className="card p-4 border-l-4 border-purple-500">
                                <div className="text-sm text-gray-600">总成本</div>
                                <div className="metric-value text-purple-600">${{(summary.total_cost || 0).toFixed(2)}}</div>
                            </div>
                        </div>
                        
                        {/* Alerts Section */}}
                        {{alerts.length > 0 && (
                            <div className="mb-8">
                                <h3 className="text-lg font-semibold mb-4">⚠️ 系统告警</h3>
                                <div className="space-y-2">
                                    {{alerts.map((alert, idx) => (
                                        <div key={{idx}} className={{`card p-4 border-l-4 ${{
                                            alert.level === 'action-required' ? 'border-red-500 bg-red-50' :
                                            alert.level === 'warn' ? 'border-yellow-500 bg-yellow-50' :
                                            'border-blue-500 bg-blue-50'
                                        }}`}}>
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <span className={{`badge ${{
                                                        alert.level === 'action-required' ? 'badge-red' :
                                                        alert.level === 'warn' ? 'badge-yellow' :
                                                        'badge-blue'
                                                    }} mr-2`}}>
                                                        {{alert.level}}
                                                    </span>
                                                    <span className="font-medium">{{alert.code}}</span>
                                                </div>
                                                {{alert.count > 0 && (
                                                    <span className="text-sm text-gray-500">数量: {{alert.count}}</span>
                                                )}}
                                            </div>
                                            <p className="mt-2 text-gray-700">{{alert.message}}</p>
                                        </div>
                                    ))}}
                                </div>
                            </div>
                        )}}
                        
                        {/* Sessions by Agent */}}
                        <div className="mb-8">
                            <h3 className="text-lg font-semibold mb-4">📋 Sessions详情（按Agent分组）</h3>
                            {{Object.entries(sessionsByAgent).map(([agentId, agentSessions]) => (
                                <div key={{agentId}} className="card mb-4 overflow-hidden">
                                    <div className="bg-gray-50 px-4 py-3 border-b">
                                        <div className="flex items-center justify-between">
                                            <span className="font-semibold">{{agentId}}</span>
                                            <span className="text-sm text-gray-500">{{agentSessions.length}} sessions</span>
                                        </div>
                                    </div>
                                    <table className="w-full">
                                        <thead className="bg-gray-50 text-xs text-gray-600">
                                            <tr>
                                                <th className="text-left py-2 px-4">Session</th>
                                                <th className="text-left py-2 px-4">状态</th>
                                                <th className="text-right py-2 px-4">Tokens</th>
                                                <th className="text-right py-2 px-4">成本</th>
                                                <th className="text-right py-2 px-4">消息</th>
                                                <th className="text-left py-2 px-4">Tools</th>
                                                <th className="text-left py-2 px-4">错误</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {{agentSessions.map((s) => (
                                                <tr key={{s.session_key}} className="border-b hover:bg-gray-50">
                                                    <td className="py-3 px-4 font-mono text-sm">{{s.session_key.substring(0, 16)}}...</td>
                                                    <td className="py-3 px-4">
                                                        <span className={{`badge ${{
                                                            s.state === 'running' ? 'badge-green' :
                                                            s.state === 'error' ? 'badge-red' :
                                                            s.state === 'blocked' ? 'badge-yellow' :
                                                            'badge-blue'
                                                        }}`}}>
                                                            {{s.state}}
                                                        </span>
                                                    </td>
                                                    <td className="py-3 px-4 text-right">{{s.tokens_total?.toLocaleString()}}</td>
                                                    <td className="py-3 px-4 text-right">${{s.cost?.toFixed(4)}}</td>
                                                    <td className="py-3 px-4 text-right">{{s.message_count}}</td>
                                                    <td className="py-3 px-4 text-sm">{{s.tool_calls?.length || 0}}</td>
                                                    <td className="py-3 px-4">
                                                        {{s.errors?.length > 0 ? (
                                                            <span className="badge badge-red">{{s.errors.length}} errors</span>
                                                        ) : '-'}}
                                                    </td>
                                                </tr>
                                            ))}}
                                        </tbody>
                                    </table>
                                </div>
                            ))}}
                        </div>
                        
                        {/* Budget Section */}}
                        <div className="mb-8">
                            <h3 className="text-lg font-semibold mb-4">💰 预算治理</h3>
                            <div className="card overflow-hidden">
                                <div className="p-4 bg-purple-50 border-b">
                                    <div className="flex items-center justify-between">
                                        <span className="font-semibold">总预估成本</span>
                                        <span className="text-2xl font-bold text-purple-600">${{(budget.total_cost || 0).toFixed(4)}}</span>
                                    </div>
                                </div>
                                <table className="w-full">
                                    <thead className="bg-gray-50 text-sm">
                                        <tr>
                                            <th className="text-left py-3 px-4">Agent</th>
                                            <th className="text-right py-3 px-4">已用Tokens</th>
                                            <th className="text-right py-3 px-4">限制</th>
                                            <th className="text-right py-3 px-4">使用率</th>
                                            <th className="text-right py-3 px-4">成本</th>
                                            <th className="text-center py-3 px-4">状态</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {{(budget.metrics || []).map((m) => (
                                            <tr key={{m.scope_id}} className="border-b hover:bg-gray-50">
                                                <td className="py-3 px-4 font-medium">{{m.scope_id}}</td>
                                                <td className="py-3 px-4 text-right">{{m.used?.toLocaleString()}}</td>
                                                <td className="py-3 px-4 text-right">{{m.limit?.toLocaleString()}}</td>
                                                <td className="py-3 px-4 text-right">
                                                    <div className="flex items-center justify-end">
                                                        <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                                                            <div 
                                                                className={{`h-2 rounded-full ${{
                                                                    m.usage_percent > 100 ? 'bg-red-500' :
                                                                    m.usage_percent > 80 ? 'bg-yellow-500' :
                                                                    'bg-green-500'
                                                                }}`}}
                                                                style={{width: `${{Math.min(m.usage_percent, 100)}}%`}}
                                                            />
                                                        </div>
                                                        <span className={{m.usage_percent > 100 ? 'text-red-600 font-bold' : ''}}>
                                                            {{m.usage_percent}}%
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="py-3 px-4 text-right">${{m.estimated_cost?.toFixed(4)}}</td>
                                                <td className="py-3 px-4 text-center">
                                                    <span className={{`badge ${{
                                                        m.status === 'over' ? 'badge-red' :
                                                        m.status === 'warn' ? 'badge-yellow' :
                                                        'badge-green'
                                                    }}`}}>
                                                        {{m.status}}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        {/* Footer */}}
                        <div className="text-center text-sm text-gray-500 mt-8">
                            <p>数据生成时间: {{data.generated_at}}</p>
                            <p className="mt-1">💓 心跳机制: 每30秒自动刷新 | 已刷新 {{heartbeatCount}} 次</p>
                        </div>
                    </div>
                </div>
            );
        }}
        
        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<CompleteDashboard />);
    </script>
</body>
</html>'''
    
    return html

if __name__ == "__main__":
    # 生成Dashboard
    html = generate_dashboard_html()
    
    # 保存到前端目录
    output_path = Path("/Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ 完整Dashboard已生成")
    print(f"📁 位置: {output_path}")
    print("🌐 刷新 http://localhost:3000 查看")
    print("💓 心跳机制: 每30秒自动刷新数据")
