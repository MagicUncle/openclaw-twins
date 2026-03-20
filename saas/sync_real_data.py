#!/usr/bin/env python3
"""同步真实报告数据到SaaS"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Agent, Tenant
import uuid

engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
Session = sessionmaker(bind=engine)
db = Session()

# 读取真实报告
today = datetime.now().strftime("%Y-%m-%d")
report_file = Path(f'/Users/magicuncle/.openclaw/workspace/metrics/daily/{today}.json')

with open(report_file, 'r') as f:
    report = json.load(f)

tenant = db.query(Tenant).first()
if not tenant:
    print("❌ 未找到租户")
    exit(1)

print("🔄 同步真实数据到SaaS...")
print("="*60)

# 更新或创建Agent
for agent_name, stats in report.get('agents', {}).items():
    existing = db.query(Agent).filter(
        Agent.name == agent_name,
        Agent.tenant_id == tenant.id
    ).first()
    
    if existing:
        # 更新
        existing.total_calls = stats['calls']
        existing.success_rate = int(stats['success_rate'] * 100)
        existing.status = 'active'
        print(f"✅ 更新Agent: {agent_name} - {stats['calls']} 次调用, 效能分 {stats['efficiency_score']}")
    else:
        # 创建新Agent
        agent = Agent(
            id=str(uuid.uuid4()),
            name=agent_name,
            description=f'Agent {agent_name}',
            agent_type='system' if agent_name in ['zongban', 'main'] else 'worker',
            total_calls=stats['calls'],
            success_rate=int(stats['success_rate'] * 100),
            status='active',
            tenant_id=tenant.id,
            is_active=True
        )
        db.add(agent)
        print(f"✅ 创建Agent: {agent_name} - {stats['calls']} 次调用")

db.commit()

# 显示最终结果
print("\n📊 更新后的Agent列表:")
all_agents = db.query(Agent).filter(Agent.tenant_id == tenant.id).order_by(Agent.total_calls.desc()).all()
for a in all_agents:
    print(f"  • {a.name:12} ({a.agent_type:8}) - 调用:{a.total_calls:5} 成功率:{a.success_rate}%")

db.close()
print("\n🎉 真实数据同步完成！刷新 http://localhost:3000 查看")
