from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class Role(Base):
    """角色"""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    is_system = Column(Boolean, default=False)  # 系统内置角色不可删除

    users = relationship("User", back_populates="role")

    # 角色权限（简化版，可以用单独的权限表）
    permissions = Column(JSON, default=list)  # ["flow:view", "flow:execute", "host:manage"]


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    phone = Column(String(20))
    department = Column(String(100))
    is_active = Column(Boolean, default=True)
    role_id = Column(String(36), ForeignKey("roles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))

    role = relationship("Role", back_populates="users")
    owned_flows = relationship("Flow", back_populates="owner")
    flow_permissions = relationship("UserFlowPermission", back_populates="user")
    executions = relationship("FlowExecution", back_populates="user")


class UserFlowPermission(Base):
    """用户-流程权限关联表"""
    __tablename__ = "user_flow_permissions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    flow_id = Column(String(36), ForeignKey("flows.id"), nullable=False)
    actions = Column(JSON, default=list)  # ["view", "execute", "edit"]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="flow_permissions")
    flow = relationship("Flow", back_populates="permissions")
