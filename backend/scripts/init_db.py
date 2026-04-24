"""初始化数据库和默认数据"""
import asyncio
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.database import engine, async_session_maker, Base
# 导入所有模型，确保它们被注册到 Base.metadata
from app.models.user import User, Role, UserFlowPermission
from app.models.host import Host, HostGroup
from app.models.flow import Flow, FlowExecution, NodeExecution, ScheduledJob, ExecutionLog, PlaybookTemplate, ScriptTemplate
from app.models.settings import SystemSettings
from app.core.security import get_password_hash


async def init_database():
    """初始化数据库表"""
    async with engine.begin() as conn:
        # 先删除已存在的表（使用 CASCADE 删除依赖）
        await conn.execute(text("DROP TABLE IF EXISTS user_flow_permissions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS execution_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS node_executions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS flow_executions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS scheduled_jobs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS flows CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS hosts CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS credentials CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS host_groups CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS playbook_templates CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS script_templates CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS system_settings CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS roles CASCADE"))
        
        # 创建表
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成")


async def create_default_data():
    """创建默认数据"""
    async with async_session_maker() as session:
        # 创建默认角色
        roles_data = [
            {
                "name": "admin",
                "description": "超级管理员",
                "is_system": True,
                "permissions": [
                    "flow:view", "flow:create", "flow:edit", "flow:delete", "flow:execute",
                    "host:view", "host:create", "host:edit", "host:delete",
                    "user:view", "user:create", "user:edit", "user:delete",
                    "template:view", "template:create", "template:edit", "template:delete",
                    "settings:view", "settings:edit"
                ]
            },
            {
                "name": "operator",
                "description": "运维工程师",
                "is_system": False,
                "permissions": [
                    "flow:view", "flow:create", "flow:edit", "flow:execute",
                    "host:view", "host:create", "host:edit",
                    "template:view", "template:execute"
                ]
            },
            {
                "name": "user",
                "description": "普通用户",
                "is_system": True,
                "permissions": [
                    "flow:view", "flow:execute"
                ]
            }
        ]

        for role_data in roles_data:
            from sqlalchemy import select
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if not result.scalar_one_or_none():
                role = Role(**role_data)
                session.add(role)
                print(f"创建角色: {role_data['name']}")

        await session.commit()

        # 创建默认管理员用户
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if not result.scalar_one_or_none():
            admin_role = await session.execute(
                select(Role).where(Role.name == "admin")
            )
            admin_role = admin_role.scalar_one_or_none()

            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=get_password_hash("admin123"),
                full_name="系统管理员",
                role_id=admin_role.id if admin_role else None
            )
            session.add(admin)
            print("创建默认管理员用户: admin / admin123")
            await session.commit()

        # 创建默认主机组
        groups = ["Web 服务器", "数据库服务器", "应用服务器", "缓存服务器"]
        for group_name in groups:
            result = await session.execute(
                select(HostGroup).where(HostGroup.name == group_name)
            )
            if not result.scalar_one_or_none():
                group = HostGroup(name=group_name)
                session.add(group)
                print(f"创建主机组: {group_name}")

        await session.commit()

    print("\n初始化完成!")
    print("=" * 50)
    print("默认登录信息:")
    print("  用户名: admin")
    print("  密码: admin123")
    print("=" * 50)


async def main():
    await init_database()
    await create_default_data()


if __name__ == "__main__":
    asyncio.run(main())
