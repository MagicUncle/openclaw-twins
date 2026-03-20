// ProposalsPage 完整实现 - 包含详情弹窗
const ProposalsPage = ({ data, systemStatus }) => {
    const [proposals, setProposals] = useState([]);
    const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, applied: 0, rejected: 0 });
    const [selectedProposal, setSelectedProposal] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(false);

    useEffect(() => {
        fetchProposals();
    }, []);

    const fetchProposals = async () => {
        try {
            const response = await fetch('/api/v1/proposals/all');
            if (response.ok) {
                const data = await response.json();
                setProposals(data.proposals || []);
                setStats(data.statistics || {});
            } else {
                // 使用本地数据
                loadLocalProposals();
            }
        } catch (error) {
            loadLocalProposals();
        } finally {
            setLoading(false);
        }
    };

    const loadLocalProposals = () => {
        // 从systemStatus获取或模拟
        const mockProposals = [
            {
                id: "opt-wenyuan-2026-03-19",
                title: "优化 wenyuan 的效能",
                type: "optimization",
                target: "wenyuan",
                problem: "wenyuan 被评为C级，效能分仅 0.44，成功率50%",
                priority: "P0",
                effort: "medium",
                impact: "high",
                _status: "pending",
                solutions: [
                    {
                        name: "Prompt优化",
                        description: "重构系统提示，增加示例和约束",
                        steps: ["分析当前Prompt问题", "添加Few-shot示例", "增加输出格式约束"],
                        effort: "low",
                        expected_improvement: "成功率提升10-15%"
                    },
                    {
                        name: "工具链优化",
                        description: "优化工具调用顺序，减少冗余调用",
                        steps: ["分析工具调用序列", "识别冗余调用", "重构调用逻辑"],
                        effort: "medium",
                        expected_improvement: "Token消耗减少20-30%"
                    },
                    {
                        name: "添加缓存机制",
                        description: "缓存重复查询结果，减少重复计算",
                        steps: ["识别高频重复查询", "实现结果缓存", "添加缓存失效策略"],
                        effort: "medium",
                        expected_improvement: "响应时间减少40-50%"
                    }
                ],
                risks: [
                    { level: "low", description: "优化可能影响现有功能", mitigation: "建议在测试环境验证后再部署" }
                ]
            },
            {
                id: "opt-shangqing-2026-03-19",
                title: "优化 shangqing 的效能",
                type: "optimization",
                target: "shangqing",
                problem: "shangqing 成功率偏低，需要提升稳定性",
                priority: "P0",
                effort: "low",
                impact: "medium",
                _status: "pending",
                solutions: [
                    {
                        name: "错误处理增强",
                        description: "添加重试机制和错误恢复",
                        expected_improvement: "成功率提升15-20%"
                    }
                ],
                risks: [
                    { level: "low", description: "风险可控", mitigation: "按标准流程实施" }
                ]
            },
            {
                id: "skill-browser-2026-03-19",
                title: "添加 browser 技能",
                type: "new_skill",
                proposed_skill: {
                    name: "browser",
                    description: "网页浏览和内容提取能力"
                },
                priority: "P1",
                effort: "high",
                impact: "high",
                _status: "pending",
                solutions: [],
                risks: [
                    { level: "medium", description: "新技能可能引入未预期的行为", mitigation: "建议先进行充分的单元测试" }
                ]
            }
        ];
        
        setProposals(mockProposals);
        setStats({ total: 10, pending: 10, approved: 0, applied: 0, rejected: 0 });
    };

    const handleApprove = async (proposalId) => {
        setActionLoading(true);
        try {
            const response = await fetch(`/api/v1/proposals/${proposalId}/approve`, {
                method: 'POST'
            });
            if (response.ok) {
                // 更新本地状态
                setProposals(prev => prev.map(p => 
                    p.id === proposalId ? { ...p, _status: 'approved' } : p
                ));
                setStats(prev => ({ ...prev, pending: prev.pending - 1, approved: prev.approved + 1 }));
                setSelectedProposal(null);
            }
        } catch (error) {
            console.error('批准失败:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const handleReject = async (proposalId) => {
        setActionLoading(true);
        try {
            const response = await fetch(`/api/v1/proposals/${proposalId}/reject`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ reason: "用户拒绝" })
            });
            if (response.ok) {
                setProposals(prev => prev.map(p => 
                    p.id === proposalId ? { ...p, _status: 'rejected' } : p
                ));
                setStats(prev => ({ ...prev, pending: prev.pending - 1, rejected: prev.rejected + 1 }));
                setSelectedProposal(null);
            }
        } catch (error) {
            console.error('拒绝失败:', error);
        } finally {
            setActionLoading(false);
        }
    };

    const getStatusBadge = (status) => {
        const configs = {
            pending: { text: '待处理', class: 'badge-yellow' },
            approved: { text: '已批准', class: 'badge-green' },
            applied: { text: '已应用', class: 'badge-blue' },
            rejected: { text: '已拒绝', class: 'badge-red' }
        };
        const config = configs[status] || configs.pending;
        return <span className={`badge ${config.class}`}>{config.text}</span>;
    };

    const getTypeBadge = (type) => {
        const configs = {
            optimization: { text: '优化', class: 'badge-blue' },
            cost_optimization: { text: '成本优化', class: 'badge-purple' },
            new_skill: { text: '新技能', class: 'badge-green' }
        };
        const config = configs[type] || { text: type, class: 'badge-gray' };
        return <span className={`badge ${config.class}`}>{config.text}</span>;
    };

    if (loading) return <div className="p-8">加载提案数据...</div>;

    return (
        <div>
            <div className="section-title">
                <span className="icon">💡</span>
                优化提案管理
                <span className="ml-2 text-sm font-normal text-gray-500">
                    Architect自动生成的自进化建议
                </span>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-5 gap-4 mb-6">
                <div className="card p-4 text-center">
                    <div className="text-3xl font-bold text-blue-600">{stats.total}</div>
                    <div className="text-sm text-gray-600">总提案</div>
                </div>
                <div className="card p-4 text-center">
                    <div className="text-3xl font-bold text-yellow-600">{stats.pending}</div>
                    <div className="text-sm text-gray-600">待处理</div>
                </div>
                <div className="card p-4 text-center">
                    <div className="text-3xl font-bold text-green-600">{stats.approved}</div>
                    <div className="text-sm text-gray-600">已批准</div>
                </div>
                <div className="card p-4 text-center">
                    <div className="text-3xl font-bold text-purple-600">{stats.applied}</div>
                    <div className="text-sm text-gray-600">已应用</div>
                </div>
                <div className="card p-4 text-center">
                    <div className="text-3xl font-bold text-red-600">{stats.rejected}</div>
                    <div className="text-sm text-gray-600">已拒绝</div>
                </div>
            </div>

            {/* 自进化流程 */}
            <div className="card p-6 mb-6 bg-gradient-to-r from-purple-50 to-blue-50">
                <h3 className="font-bold mb-4">🔄 自进化流程</h3>
                <div className="flex items-center justify-between">
                    {[
                        { icon: "📊", title: "监控", desc: "Overseer采集数据" },
                        { icon: "🔍", title: "分析", desc: "识别能力缺口" },
                        { icon: "💡", title: "生成", desc: "Architect创建提案" },
                        { icon: "✅", title: "审批", desc: "用户确认" },
                        { icon: "🚀", title: "部署", desc: "自动应用优化" }
                    ].map((step, i) => (
                        <div key={i} className="flex-1 text-center">
                            <div className="text-3xl mb-2">{step.icon}</div>
                            <div className="font-medium">{step.title}</div>
                            <div className="text-xs text-gray-500">{step.desc}</div>
                            {i < 4 && <div className="text-2xl text-gray-300 mt-2">→</div>}
                        </div>
                    ))}
                </div>
            </div>

            {/* 提案列表 */}
            <div className="card overflow-hidden">
                <table className="w-full">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="text-left py-3 px-4">提案</th>
                            <th className="text-left py-3 px-4">类型</th>
                            <th className="text-left py-3 px-4">目标</th>
                            <th className="text-center py-3 px-4">优先级</th>
                            <th className="text-center py-3 px-4">工作量</th>
                            <th className="text-center py-3 px-4">状态</th>
                            <th className="text-right py-3 px-4">操作</th>
                        </tr>
                    </thead>
                    <tbody>
                        {proposals.map((proposal) => (
                            <tr key={proposal.id} className="border-b hover:bg-gray-50">
                                <td className="py-3 px-4">
                                    <div className="font-medium">{proposal.title}</div>
                                    <div className="text-xs text-gray-500">{proposal.id}</div>
                                </td>
                                <td className="py-3 px-4">{getTypeBadge(proposal.type)}</td>
                                <td className="py-3 px-4 font-medium">{proposal.target || '-'}</td>
                                <td className="py-3 px-4 text-center">
                                    <span className={`badge ${proposal.priority === 'P0' ? 'badge-red' : 'badge-yellow'}`}>
                                        {proposal.priority}
                                    </span>
                                </td>
                                <td className="py-3 px-4 text-center capitalize">{proposal.effort}</td>
                                <td className="py-3 px-4 text-center">{getStatusBadge(proposal._status)}</td>
                                <td className="py-3 px-4 text-right">
                                    <button 
                                        onClick={() => setSelectedProposal(proposal)}
                                        className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                                    >
                                        查看详情
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* 详情弹窗 */}
            {selectedProposal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto">
                        {/* 弹窗头部 */}
                        <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
                            <div>
                                <h2 className="text-xl font-bold">{selectedProposal.title}</h2>
                                <div className="flex items-center gap-2 mt-1">
                                    {getTypeBadge(selectedProposal.type)}
                                    <span className="badge badge-gray">{selectedProposal.id}</span>
                                    {getStatusBadge(selectedProposal._status)}
                                </div>
                            </div>
                            <button 
                                onClick={() => setSelectedProposal(null)}
                                className="text-gray-500 hover:text-gray-700 text-2xl"
                            >
                                ×
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            {/* 问题描述 */}
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <h3 className="font-semibold text-red-900 mb-2">🔍 问题描述</h3>
                                <p className="text-red-800">{selectedProposal.problem}</p>
                                {selectedProposal.problem_metrics && (
                                    <div className="mt-2 text-sm text-red-700">
                                        <div>效能分: {selectedProposal.problem_metrics.efficiency_score}</div>
                                        <div>成功率: {(selectedProposal.problem_metrics.success_rate * 100).toFixed(0)}%</div>
                                        <div>调用次数: {selectedProposal.problem_metrics.calls}</div>
                                    </div>
                                )}
                            </div>

                            {/* 解决方案 */}
                            {selectedProposal.solutions && selectedProposal.solutions.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3">💡 解决方案 ({selectedProposal.solutions.length}个)</h3>
                                    <div className="space-y-3">
                                        {selectedProposal.solutions.map((sol, idx) => (
                                            <div key={idx} className="border rounded-lg p-4 hover:shadow-md transition">
                                                <div className="flex justify-between items-start mb-2">
                                                    <h4 className="font-medium">{sol.name}</h4>
                                                    <span className="text-xs bg-gray-100 px-2 py-1 rounded capitalize">{sol.effort}</span>
                                                </div>
                                                <p className="text-gray-600 text-sm mb-2">{sol.description}</p>
                                                {sol.steps && (
                                                    <div className="text-sm text-gray-500 mb-2">
                                                        <span className="font-medium">实施步骤:</span>
                                                        <ol className="list-decimal list-inside ml-2 mt-1">
                                                            {sol.steps.map((step, i) => (
                                                                <li key={i}>{step}</li>
                                                            ))}
                                                        </ol>
                                                    </div>
                                                )}
                                                {sol.expected_improvement && (
                                                    <div className="text-sm text-green-600">
                                                        <span className="font-medium">预期效果:</span> {sol.expected_improvement}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* 风险分析 */}
                            {selectedProposal.risks && selectedProposal.risks.length > 0 && (
                                <div>
                                    <h3 className="font-semibold mb-3">⚠️ 风险分析</h3>
                                    <div className="space-y-2">
                                        {selectedProposal.risks.map((risk, idx) => (
                                            <div key={idx} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className={`badge ${risk.level === 'high' ? 'badge-red' : risk.level === 'medium' ? 'badge-yellow' : 'badge-green'}`}>
                                                        {risk.level}
                                                    </span>
                                                    <span className="font-medium">{risk.description}</span>
                                                </div>
                                                <div className="text-sm text-gray-600 ml-16">
                                                    <span className="font-medium">缓解措施:</span> {risk.mitigation}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* 元信息 */}
                            <div className="grid grid-cols-4 gap-4 text-sm bg-gray-50 p-4 rounded-lg">
                                <div>
                                    <span className="text-gray-500">优先级:</span>
                                    <span className="ml-2 font-medium">{selectedProposal.priority}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">工作量:</span>
                                    <span className="ml-2 font-medium capitalize">{selectedProposal.effort}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">影响:</span>
                                    <span className="ml-2 font-medium capitalize">{selectedProposal.impact}</span>
                                </div>
                                <div>
                                    <span className="text-gray-500">自动应用:</span>
                                    <span className="ml-2 font-medium">{selectedProposal.auto_apply ? '是' : '否'}</span>
                                </div>
                            </div>
                        </div>

                        {/* 操作按钮 */}
                        {selectedProposal._status === 'pending' && (
                            <div className="sticky bottom-0 bg-white border-t px-6 py-4 flex justify-end gap-3">
                                <button 
                                    onClick={() => handleReject(selectedProposal.id)}
                                    disabled={actionLoading}
                                    className="px-6 py-2 border border-red-300 text-red-700 rounded-lg hover:bg-red-50 disabled:opacity-50"
                                >
                                    {actionLoading ? '处理中...' : '拒绝'}
                                </button>
                                <button 
                                    onClick={() => handleApprove(selectedProposal.id)}
                                    disabled={actionLoading}
                                    className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                                >
                                    {actionLoading ? '处理中...' : '批准'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

// 导出供Dashboard使用
window.ProposalsPage = ProposalsPage;
