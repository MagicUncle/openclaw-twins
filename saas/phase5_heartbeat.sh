#!/bin/bash
# 任务完成确认心跳 - Phase 5

echo "💓 Phase 5 任务完成确认心跳"
echo "=============================="
echo ""

# 检查任务1：数据真实化
echo "任务1: 数据100%真实化"
if [ -f "/Users/magicuncle/.openclaw/workspace/saas/validate_real_data.py" ]; then
    cd /Users/magicuncle/.openclaw/workspace/saas
    source venv/bin/activate
    python3 validate_real_data.py 2>/dev/null | grep -q "数据100%真实化检查通过"
    if [ $? -eq 0 ]; then
        echo "  ✅ 通过"
    else
        echo "  ❌ 未通过"
    fi
else
    echo "  ❌ 验证脚本不存在"
fi

# 检查任务2.1：提案管理器
echo ""
echo "任务2.1: 提案管理器"
if [ -f "/Users/magicuncle/.openclaw/workspace/agents/overseer/scripts/proposal_manager.py" ]; then
    echo "  ✅ 提案管理器已创建"
else
    echo "  ❌ 提案管理器不存在"
fi

# 检查任务2.2：API端点
echo ""
echo "任务2.2: API端点"
if grep -q "/proposals/all" /Users/magicuncle/.openclaw/workspace/saas/backend/src/api/v1/router.py; then
    echo "  ✅ API端点已添加"
else
    echo "  ❌ API端点未添加"
fi

# 检查任务2.3：前端详情弹窗
echo ""
echo "任务2.3: 前端详情弹窗"
if grep -q "ProposalModal" /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html; then
    echo "  ✅ 详情弹窗已集成"
else
    echo "  ❌ 详情弹窗未集成"
fi

# 检查任务3：前后端统一
echo ""
echo "任务3: 前后端统一（批准/拒绝操作）"
if grep -q "handleApprove" /Users/magicuncle/.openclaw/workspace/saas/frontend/public/index.html; then
    echo "  ✅ 操作按钮已集成"
else
    echo "  ❌ 操作按钮未集成"
fi

echo ""
echo "=============================="
echo "刷新 http://localhost:3000 查看完整功能"
