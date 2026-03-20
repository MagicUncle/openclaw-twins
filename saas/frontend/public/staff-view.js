// StaffView 组件 - Phase 1 集成
const StaffView = ({ onBack }) => {
    const [staffData, setStaffData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStaffData();
    }, []);

    const fetchStaffData = async () => {
        try {
            const response = await fetch('/api/v1/staff');
            const data = await response.json();
            setStaffData(data);
        } catch (error) {
            console.error('获取Staff数据失败:', error);
            // 使用模拟数据
            setStaffData({
                summary: {
                    total_agents: 4,
                    truly_active: 2,
                    only_queued: 1,
                    idle: 1,
                    blocked: 0
                },
                entries: [
                    { agent_id: "zongban", status: "running", is_truly_active: true, current_task: "处理用户请求", queue_depth: 0 },
                    { agent_id: "main", status: "running", is_truly_active: true, current_task: "执行数据分析", queue_depth: 2 },
                    { agent_id: "job-agent", status: "queued", is_truly_active: false, current_task: "排队等待", queue_depth: 5 },
                    { agent_id: "wenyuan", status: "idle", is_truly_active: false, current_task: null, queue_depth: 0 }
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
    if (!staffData) return <div className="p-8">无数据</div>;

    return (
        <div className="p-8">
            <div className="flex items-center mb-6">
                <button onClick={onBack} className="mr-4 px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200">
                    ← 返回
                </button>
                <h2 className="text-2xl font-bold">👥 Staff 视图</h2>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
                <div className="card p-4 text-center">
                    <div className="text-2xl font-bold text-gray-900">{staffData.summary.total_agents}</div>
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

            {/* 说明 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <h4 className="font-semibold text-blue-900 mb-2">💡 Staff 视图说明</h4>
                <ul className="text-sm text-blue-800 space-y-1">
                    <li>• <strong>真正活跃</strong>: 当前正在执行任务的Agent（过去5分钟有活动）</li>
                    <li>• <strong>仅排队</strong>: 有积压工作但当前未执行的Agent</li>
                    <li>• <strong>空闲</strong>: 无待处理工作的Agent</li>
                    <li>• <strong>被阻塞</strong>: 遇到错误或等待资源的Agent</li>
                </ul>
            </div>

            {/* Agent列表 */}
            <div className="card overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                        <tr>
                            <th className="text-left py-3 px-4 font-medium text-gray-600">Agent</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-600">状态</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-600">当前任务</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-600">队列深度</th>
                            <th className="text-left py-3 px-4 font-medium text-gray-600">活跃度</th>
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
                                    <td className="py-4 px-4 text-gray-600">
                                        {entry.current_task || '-'}
                                    </td>
                                    <td className="py-4 px-4">
                                        {entry.queue_depth > 0 ? (
                                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-yellow-100 text-yellow-700 font-medium">
                                                {entry.queue_depth}
                                            </span>
                                        ) : (
                                            <span className="text-gray-400">0</span>
                                        )}
                                    </td>
                                    <td className="py-4 px-4">
                                        {entry.is_truly_active ? (
                                            <span className="text-green-600 font-medium">真正活跃</span>
                                        ) : entry.status === 'queued' ? (
                                            <span className="text-yellow-600">仅排队</span>
                                        ) : (
                                            <span className="text-gray-400">-</span>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>

            {/* 最后更新时间 */}
            <div className="mt-4 text-sm text-gray-500 text-right">
                最后更新: {new Date(staffData.generated_at).toLocaleString('zh-CN')}
            </div>
        </div>
    );
};

// 导出供主应用使用
window.StaffView = StaffView;
