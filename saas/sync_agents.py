#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Agent, Tenant
import uuid
import json

engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
Session = sessionmaker(bind=engine)
db = Session()

# 获取租户
tenant = db.query(Tenant).first()
if tenant:
    # 从Overseer报告读取Agent
    report_path = '/Users/magicuncle/.openclaw/workspace/metrics/daily/2026-03-19.json'
    try:
        with open(report_path) as f:
            report = json.load(f)
        
        agents_data = report.get('agents', {})
        
        # 添加业务Agent
        for agent_name, stats in agents_data.items():
            existing = db.query(Agent).filter(Agent.name == agent_name, Agent.tenant_id == tenant.id).first()
            if not existing:
                agent = Agent(
                    id=str(uuid.uuid4()),
                    name=agent_name,
                    description=f'Agent {agent_name}',
                    agent_type='worker',
                    total_calls=stats.get('calls', 0),
                    success_rate=int(stats.get('success_rate', 1.0) * 100),
                    status='active',
                    tenant_id=tenant.id,
                    is_active=True
                )
                db.add(agent)
                print(f'✅ 添加Agent: {agent_name}')
        
        # 添加系统Agent（Overseer和Architect）
        for sys_name in ['overseer', 'architect']:
            existing = db.query(Agent).filter(Agent.name == sys_name, Agent.tenant_id == tenant.id).first()
            if not existing:
                sys_agent = Agent(
                    id=str(uuid.uuid4()),
                    name=sys_name,
                    description=f'System Agent: {sys_name}',
                    agent_type='system',
                    total_calls=0,
                    success_rate=100,
                    status='active',
                    tenant_id=tenant.id,
                    is_active=True
                )
                db.add(sys_agent)
                print(f'✅ 添加系统Agent: {sys_name}')
        
        db.commit()
        
        # 显示所有Agent
        print('\n📋 SaaS中的Agent列表:')
        all_agents = db.query(Agent).filter(Agent.tenant_id == tenant.id).all()
        for a in all_agents:
            print(f'  • {a.name} ({a.agent_type}) - 调用:{a.total_calls} 成功率:{a.success_rate}%')
        
    except Exception as e:
        print(f'⚠️ 错误: {e}')
        import traceback
        traceback.print_exc()
else:
    print('❌ 未找到租户')

db.close()
