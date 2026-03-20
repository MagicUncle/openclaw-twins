#!/bin/bash
# Heartbeat Monitor - 心跳确认脚本
# 持续监控系统运行状态，每30秒刷新数据

echo "💓 OpenClaw Agent OS - 心跳确认系统"
echo "======================================"
echo ""

# 检查后端服务
check_backend() {
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ 后端服务运行正常 (http://localhost:8000)"
        return 0
    else
        echo "❌ 后端服务未响应"
        return 1
    fi
}

# 检查前端服务
check_frontend() {
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ 前端服务运行正常 (http://localhost:3000)"
        return 0
    else
        echo "❌ 前端服务未响应"
        return 1
    fi
}

# 刷新数据采集
refresh_data() {
    echo "🔄 刷新数据采集..."
    cd /Users/magicuncle/.openclaw/workspace/agents/overseer/scripts
    python3 full_data_collector.py > /tmp/heartbeat.log 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ 数据采集成功"
    else
        echo "⚠️ 数据采集有警告，继续运行"
    fi
}

# 主循环
counter=0
while true; do
    clear
    echo "💓 OpenClaw Agent OS - 心跳确认系统"
    echo "======================================"
    echo ""
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "心跳次数: $counter"
    echo ""
    
    # 检查服务
    check_backend
    check_frontend
    echo ""
    
    # 刷新数据
    refresh_data
    echo ""
    
    # 显示访问地址
    echo "🌐 访问地址:"
    echo "  • Dashboard: http://localhost:3000"
    echo "  • API文档: http://localhost:8000/docs"
    echo ""
    echo "📊 完整数据指标:"
    echo "  • Sessions: 完整session详情（状态、token、成本）"
    echo "  • Budget: 预算治理（使用率、成本、告警）"
    echo "  • Alerts: 系统告警（阻塞、错误、审批）"
    echo "  • Heartbeat: 每30秒自动刷新"
    echo ""
    echo "按 Ctrl+C 停止心跳监控"
    
    counter=$((counter + 1))
    sleep 30
done
