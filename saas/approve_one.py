#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Proposal
from datetime import datetime

engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
Session = sessionmaker(bind=engine)
db = Session()

# 批准一个提案
proposal = db.query(Proposal).filter(Proposal.id == "opt-wenyuan-2026-03-19").first()
if proposal:
    proposal.status = "approved"
    db.commit()
    print(f"✅ 已批准提案: {proposal.title}")
else:
    print("❌ 未找到提案")

db.close()
