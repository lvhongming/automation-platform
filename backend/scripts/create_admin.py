#!/usr/bin/env python3
"""
创建管理员用户脚本
"""
import asyncio
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import async_session_maker

# 导入所有模型以确保关系正确解析
from app.models.user import User, Role
from app.models.host import Host, HostGroup, Credential
from app.models.flow import Flow, FlowExecution, NodeExecution, ScheduledJob, ExecutionLog, PlaybookTemplate, ScriptTemplate
from app.models.settings import SystemSettings

from app.core.security import get_password_hash


async def create_admin_user(username: str = "admin", password: str = "admin123"):
    """创建管理员用户"""
    async with async_session_maker() as session:
        # 获取 admin 角色
        from sqlalchemy import select
        result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()

        if not admin_role:
            print("错误: admin 角色不存在")
            return False

        # 检查用户是否已存在
        result = await session.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"用户 {username} 已存在，正在更新密码...")
            existing_user.password_hash = get_password_hash(password)
            await session.commit()
            print(f"密码已更新")
            return True

        # 创建新用户
        admin = User(
            username=username,
            email="admin@example.com",
            password_hash=get_password_hash(password),
            full_name="系统管理员",
            role_id=admin_role.id
        )
        session.add(admin)
        await session.commit()

        print(f"管理员用户创建成功!")
        print(f"用户名: {username}")
        print(f"密码: {password}")
        return True


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"

    success = asyncio.run(create_admin_user(username, password))
    sys.exit(0 if success else 1)
