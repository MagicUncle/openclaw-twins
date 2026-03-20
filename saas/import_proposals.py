#!/usr/bin/env python3
"""导入文件系统中的提案到SaaS数据库"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Proposal, Tenant

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
PROPOSALS_DIR = WORKSPACE / "metrics" / "proposals"

def import_proposals():
    engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # 获取租户
    tenant = db.query(Tenant).first()
    if not tenant:
        print("❌ 未找到租户")
        return
    
    # 扫描提案目录
    today = datetime.now().strftime("%Y-%m-%d")
    today_dir = PROPOSALS_DIR / today
    
    if not today_dir.exists():
        print(f"⚠️ 今日提案目录不存在: {today_dir}")
        return
    
    imported = 0
    for json_file in today_dir.glob("*.json"):
        if json_file.name == "summary.json":
            continue
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            proposal_id = data.get('id')
            if not proposal_id:
                continue
            
            # 检查是否已存在
            existing = db.query(Proposal).filter(Proposal.id == proposal_id).first()
            if existing:
                continue
            
            # 创建提案记录
            proposal = Proposal(
                id=proposal_id,
                title=data.get('title', 'Untitled'),
                description=data.get('problem', ''),
                proposal_type=data.get('type', 'optimization'),
                status="pending",  # 默认pending
                priority=data.get('priority', 'P2'),
                content=json.dumps(data),
                tenant_id=tenant.id
            )
            
            db.add(proposal)
            imported += 1
            print(f"✅ 导入提案: {proposal_id}")
            
        except Exception as e:
            print(f"⚠️ 导入失败 {json_file.name}: {e}")
    
    db.commit()
    print(f"\n🎉 共导入 {imported} 个提案")
    
    # 显示所有提案
    all_proposals = db.query(Proposal).filter(Proposal.tenant_id == tenant.id).all()
    print(f"\n📋 数据库中共有 {len(all_proposals)} 个提案:")
    for p in all_proposals:
        print(f"  - {p.id}: {p.title} [{p.status}]")
    
    db.close()

if __name__ == "__main__":
    import_proposals()
