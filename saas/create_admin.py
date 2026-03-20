#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/magicuncle/.openclaw/workspace/saas/backend/src')

import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.models import Base, Tenant, User, UserRole, TenantStatus, PlanType
# from services.auth import get_password_hash
# 简化版密码哈希（仅用于演示）
def get_password_hash(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

# 连接数据库
engine = create_engine('sqlite:////Users/magicuncle/.openclaw/workspace/saas/agent_os.db')
Session = sessionmaker(bind=engine)
db = Session()

print("🎯 创建管理员账户...")

# 1. 创建租户（如果不存在）
tenant_id = str(uuid.uuid4())
tenant = db.query(Tenant).filter(Tenant.slug == "admin-tenant").first()

if not tenant:
    tenant = Tenant(
        id=tenant_id,
        name="Admin Tenant",
        slug="admin-tenant",
        status=TenantStatus.ACTIVE,
        plan=PlanType.ENTERPRISE,
        max_agents=100,
        max_calls_per_month=100000,
        email="admin@example.com"
    )
    db.add(tenant)
    db.commit()
    print(f"✅ 租户创建成功: {tenant.name}")
else:
    tenant_id = tenant.id
    print(f"✅ 使用现有租户: {tenant.name}")

# 2. 创建管理员用户
admin_id = str(uuid.uuid4())
existing_admin = db.query(User).filter(User.email == "admin@example.com").first()

if existing_admin:
    existing_admin.hashed_password = get_password_hash("admin")
    existing_admin.is_superuser = True
    existing_admin.role = UserRole.ADMIN
    db.commit()
    print(f"✅ 管理员密码已更新: admin@example.com")
else:
    admin = User(
        id=admin_id,
        email="admin@example.com",
        hashed_password=get_password_hash("admin"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True,
        tenant_id=tenant_id,
        api_key=str(uuid.uuid4()).replace("-", ""),
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    print(f"✅ 管理员创建成功: admin@example.com")

print("")
print("="*50)
print("🎉 管理员账户信息")
print("="*50)
print("邮箱: admin@example.com")
print("密码: admin")
print("角色: ADMIN (超级管理员)")
print("租户: Admin Tenant")
print("="*50)

db.close()
