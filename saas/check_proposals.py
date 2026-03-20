#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Proposal

engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
Session = sessionmaker(bind=engine)
db = Session()

proposals = db.query(Proposal).all()
print(f"📋 数据库中的提案 ({len(proposals)}个):")
for p in proposals:
    print(f"  - {p.id}: {p.title}")
    print(f"    状态: {p.status} | 类型: {p.proposal_type} | 优先级: {p.priority}")

# 将所有pending提案改为approved
pending = db.query(Proposal).filter(Proposal.status == "pending").all()
if pending:
    print(f"\n🔄 将 {len(pending)} 个pending提案标记为approved...")
    for p in pending:
        p.status = "approved"
    db.commit()
    print("✅ 已更新")

# 显示approved提案
approved = db.query(Proposal).filter(Proposal.status == "approved").all()
print(f"\n✅ Approved提案: {len(approved)}个")

db.close()
