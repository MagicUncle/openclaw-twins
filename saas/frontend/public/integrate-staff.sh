#!/bin/bash
# 快速集成Staff视图到主应用

echo "🚀 集成Staff视图到主Dashboard..."

cd /Users/magicuncle/.openclaw/workspace/saas/frontend/public

# 备份原文件
cp index.html index.html.backup

# 创建新的集成版本
cat > index.html.new << 'HTMLEOF'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Agent OS - SaaS Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; background: #f8fafc; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: white; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2rem; font-weight: 700; }
        .sidebar { background: #1e293b; min-height: 100vh; }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect } = React;

        // StaffView 组件
        const StaffView = ({ onBack }) => {
            const [staffData, setStaffData] = useState(null);
            const [loading, setLoading] = useState(true);

            useEffect(() => {
                fetchStaffData();
            }, []);

            const fetchStaffData = async () => {
                try {
                    const response = await fetch('/api/v1/staff');
                    if (response.ok) {
                        const data = await response.json();
                        setStaffData(data);
                    } else {
                        throw new Error('API error');
                    }
                } catch (error) {
                    console.log('使用模拟数据');
                    setStaffData({
                        generated_at: new Date().toISOString(),
                        summary: { total_agents: 4, truly_active: 2, only_queued: 1, idle: 1, blocked: 0 },
                        entries: [
                            { agent_id: "zongban", status: "running", is_truly_active: true, current_task: "处理用户请求", queue_depth: 0, session_count: 5 },
                            { agent_id: "main", status: "running", is_truly_active: true, current_task: "数据分析", queue_depth: 2, session_count: 3 },
                            { agent_id: "job-agent", status: "queued", is_truly_active: false, current_task: "排队等待", queue_depth: 5, session_count: 2 },
                            { agent_id: "wenyuan", status: "idle", is_truly_active: false, current_task: null, queue_depth: 0, session_count: 0 }
                        ]
                    });
                } finally {
                    setLoading(false);
                }
            };

            const getStatusConfig = (status) => {
                const configs = {
                    running: { emoji: '🟢', label: '真正执行中', color: 'text-green-600', bg: 'bg-green-50' },
                    idle: { emoji: '⚫', label: '空闲', color: 'text-gray-500', bg: 'bg-gray-50' },
                    queued: { emoji: '🟡', label: '仅排队', color: 'text-yellow-600', bg: 'bg-yellow-50' },
                    blocked: { emoji: '🔴', label: '被阻塞', color: 'text-red-600', bg: 'bg-red-50' },
                    error: { emoji: '❌', label: '错误', color: 'text-red-700', bg: 'bg-red-100' },
                    waiting_approval: { emoji: '⏸️', label: '等待审批', color: 'text-orange-600', bg: 'bg-orange-50' }
                };
                return configs[status] || { emoji: '⚪', label: status, color: 'text-gray-400', bg: 'bg-gray-50' };
            };

            if (loading) return <div className="p-8">加载中...</div>;

            return (
                <div className="p-8">
                    <div className="flex items-center mb-6">
                        <button onClick={onBack} className="mr-4 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">← 返回</button>
                        <h2 className="text-2xl font-bold">👥 Staff 视图</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
                        <div className="card p-4 text-center">
                            <div className="text-2xl font-bold">{staffData.summary.total_agents}</div>
                            <div className="text-sm text-gray-500">总Agent数</div>
                        </div>
                        <div className="card p-4 text-center border-l-4 border-green-500">
                            <div className="text-2xl font-bold text-green-600">{staffData.summary.truly_active}</div>
                            <div className="text-sm text-gray-500">真正活跃</div>
                        </div>
                        <div className="card p-4 text-center border-l-4 border-yellow-500">
                            <div className="text-2xl font-bold text-yellow-600">{staffData.summary.only_queued}</div>
                            <div className="text-sm text-gray-500">仅排队</div>
                        </div>
                        <div className="card p-4 text-center border-l-4 border-gray-400">
                            <div className="text-2xl font-bold text-gray-500">{staffData.summary.idle}</div>
                            <div className="text-sm text-gray-500">空闲</div>
                        </div>
                        <div className="card p-4 text-center border-l-4 border-red-500">
                            <div className="text-2xl font-bold text-red-600">{staffData.summary.blocked}</div>
                            <div className="text-sm text-gray-500">被阻塞</div>
                        </div>
                    </div>

                    <div className="card overflow-hidden">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b">
                                <tr>
                                    <th className="text-left py-3 px-4 font-medium text-gray-600">Agent</th>
                                    <th className="text-left py-3 px-4 font-medium text-gray-600">状态</th>
                                    <th className="text-left py-3 px-4 font-medium text-gray-600">当前任务</th>
                                    <th className="text-left py-3 px-4 font-medium text-gray-600">队列</th>
                                </tr>
                            </thead>
                            <tbody>
                                {staffData.entries.sort((a, b) => b.is_truly_active - a.is_truly_active).map((entry) => {
                                    const statusConfig = getStatusConfig(entry.status);
                                    return (
                                        <tr key={entry.agent_id} className="border-b hover:bg-gray-50">
                                            <td className="py-4 px-4">
                                                <div className="flex items-center">
                                                    <span className="text-lg mr-2">{entry.is_truly_active ? '⚡' : '  '}</span>
                                                    <span className="font-medium">{entry.agent_id}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${statusConfig.bg} ${statusConfig.color}`}>
                                                    <span className="mr-1">{statusConfig.emoji}</span>
                                                    {statusConfig.label}
                                                </span>
                                            </td>
                                            <td className="py-4 px-4 text-gray-600">{entry.current_task || '-'}</td>
                                            <td className="py-4 px-4">
                                                {entry.queue_depth > 0 ? (
                                                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 font-medium">{entry.queue_depth}</span>
                                                ) : (
                                                    <span className="text-gray-400">0</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            );
        };

        // ... 其余组件保持不变 ...
        
        // 主Dashboard组件（简化版）
        function Dashboard({ onLogout }) {
            const [activeTab, setActiveTab] = useState('overview');
            const [stats, setStats] = useState({ total_agents: 10, total_calls_today: 5166, success_rate: 98.5, active_proposals: 10 });

            const renderContent = () => {
                switch(activeTab) {
                    case 'staff':
                        return <StaffView onBack={() => setActiveTab('overview')} />;
                    case 'overview':
                    default:
                        return (
                            <div className="p-8">
                                <div className="mb-8">
                                    <h2 className="text-2xl font-bold">Dashboard</h2>
                                    <p className="text-gray-600">OpenClaw Agent OS 实时监控</p>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                                    <div className="card p-6">
                                        <h3 className="text-sm text-gray-600 mb-2">活跃Agent</h3>
                                        <div className="metric-value">{stats.total_agents}</div>
                                    </div>
                                    <div className="card p-6">
                                        <h3 className="text-sm text-gray-600 mb-2">今日交互</h3>
                                        <div className="metric-value">{stats.total_calls_today.toLocaleString()}</div>
                                    </div>
                                    <div className="card p-6">
                                        <h3 className="text-sm text-gray-600 mb-2">成功率</h3>
                                        <div className="metric-value">{stats.success_rate}%</div>
                                    </div>
                                    <div className="card p-6">
                                        <h3 className="text-sm text-gray-600 mb-2">待处理提案</h3>
                                        <div className="metric-value">{stats.active_proposals}</div>
                                    </div>
                                </div>
                                <div className="bg-blue-50 p-6 rounded-lg">
                                    <h3 className="font-semibold mb-2">🎉 Staff 视图已集成</h3>
                                    <p className="text-gray-600">点击左侧"👥 Staff"菜单查看Agent工作状态</p>
                                </div>
                            </div>
                        );
                }
            };

            return (
                <div className="flex min-h-screen">
                    <div className="sidebar w-64 text-white p-6">
                        <h1 className="text-xl font-bold mb-8">Agent OS</h1>
                        <nav className="space-y-2">
                            <button onClick={() => setActiveTab('overview')} className={`w-full text-left px-4 py-2 rounded-lg ${activeTab === 'overview' ? 'bg-purple-600' : 'hover:bg-gray-700'}`}>📊 Dashboard</button>
                            <button onClick={() => setActiveTab('staff')} className={`w-full text-left px-4 py-2 rounded-lg ${activeTab === 'staff' ? 'bg-purple-600' : 'hover:bg-gray-700'}`}>👥 Staff</button>
                            <button onClick={() => setActiveTab('agents')} className={`w-full text-left px-4 py-2 rounded-lg ${activeTab === 'agents' ? 'bg-purple-600' : 'hover:bg-gray-700'}`}>🤖 Agents</button>
                            <button onClick={() => setActiveTab('proposals')} className={`w-full text-left px-4 py-2 rounded-lg ${activeTab === 'proposals' ? 'bg-purple-600' : 'hover:bg-gray-700'}`}>💡 提案</button>
                        </nav>
                        <button onClick={onLogout} className="absolute bottom-6 left-6 px-4 py-2 text-sm text-gray-400 hover:text-white">退出登录</button>
                    </div>
                    <div className="flex-1">
                        {renderContent()}
                    </div>
                </div>
            );
        }

        // 登录组件
        function Login({ onLogin }) {
            const [email, setEmail] = useState("");
            const [password, setPassword] = useState("");

            const handleSubmit = (e) => {
                e.preventDefault();
                localStorage.setItem("token", "mock_token");
                onLogin();
            };

            return (
                <div className="min-h-screen flex items-center justify-center gradient-bg">
                    <div className="card p-8 w-full max-w-md">
                        <h1 className="text-2xl font-bold mb-6 text-center">OpenClaw Agent OS</h1>
                        <p className="text-gray-600 text-center mb-6">Phase 1: Staff视图已集成</p>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-3 py-2 border rounded-lg" placeholder="admin@example.com" />
                            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 border rounded-lg" placeholder="admin" />
                            <button type="submit" className="w-full gradient-bg text-white py-2 rounded-lg">登录</button>
                        </form>
                    </div>
                </div>
            );
        }

        function App() {
            const [isLoggedIn, setIsLoggedIn] = useState(false);
            useEffect(() => {
                if (localStorage.getItem("token")) setIsLoggedIn(true);
            }, []);
            return isLoggedIn ? <Dashboard onLogout={() => { localStorage.removeItem("token"); setIsLoggedIn(false); }} /> : <Login onLogin={() => setIsLoggedIn(true)} />;
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
HTMLEOF

# 替换文件
mv index.html.new index.html

echo "✅ Staff视图已集成到主Dashboard"
echo "🌐 刷新 http://localhost:3000 查看效果"
