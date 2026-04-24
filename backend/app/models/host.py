from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class HostGroup(Base):
    """主机组"""
    __tablename__ = "host_groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hosts = relationship("Host", back_populates="group")


class Credential(Base):
    """认证凭据"""
    __tablename__ = "credentials"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # password, ssh_key
    username = Column(String(100))
    password = Column(String(255))  # 加密存储
    private_key = Column(Text)
    passphrase = Column(String(255))  # 私钥密码，加密存储
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    hosts = relationship("Host", back_populates="credential")


class Host(Base):
    """主机"""
    __tablename__ = "hosts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    port = Column(Integer, default=22)
    host_type = Column(String(20), default="server")  # server, service
    service_name = Column(String(100))  # 如 nginx, mysql
    description = Column(String(255))
    group_id = Column(String(36), ForeignKey("host_groups.id"))
    credential_id = Column(String(36), ForeignKey("credentials.id"))
    variables = Column(JSON, default=dict)  # 主机变量
    tags = Column(JSON, default=list)  # 标签列表
    status = Column(String(20), default="unknown")  # online, offline, unknown
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    group = relationship("HostGroup", back_populates="hosts")
    credential = relationship("Credential", back_populates="hosts")
