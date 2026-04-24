from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class Flow(Base):
    """自动化流程"""
    __tablename__ = "flows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    flow_data = Column(JSON, default=dict)  # 节点和连线数据
    variables = Column(JSON, default=dict)  # 流程变量
    status = Column(String(20), default="draft")  # draft, published
    tags = Column(JSON, default=list)
    owner_id = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner = relationship("User", back_populates="owned_flows")
    permissions = relationship("UserFlowPermission", back_populates="flow")
    executions = relationship("FlowExecution", back_populates="flow")
    scheduled_jobs = relationship("ScheduledJob", back_populates="flow")


class PlaybookTemplate(Base):
    """Playbook 模板"""
    __tablename__ = "playbook_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)  # YAML 内容
    category = Column(String(50))  # 分类
    variables_schema = Column(JSON, default=dict)  # 变量定义
    tags = Column(JSON, default=list)
    is_public = Column(Boolean, default=True)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScriptTemplate(Base):
    """脚本模板"""
    __tablename__ = "script_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    script_type = Column(String(20), nullable=False)  # shell, python, powershell
    content = Column(Text, nullable=False)
    category = Column(String(50))
    tags = Column(JSON, default=list)
    is_public = Column(Boolean, default=True)
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FlowExecution(Base):
    """流程执行记录"""
    __tablename__ = "flow_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    flow_id = Column(String(36), ForeignKey("flows.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"))
    status = Column(String(20), default="pending")  # pending, running, success, failed, stopped
    trigger_type = Column(String(20))  # manual, scheduled, api
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    result_summary = Column(JSON, default=dict)  # {"total": 5, "success": 4, "failed": 1}
    execution_data = Column(JSON, default=dict)  # 执行时的快照数据
    variables = Column(JSON, default=dict)  # 全局变量字典 {"key": "value"}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flow = relationship("Flow", back_populates="executions")
    user = relationship("User", back_populates="executions")
    node_executions = relationship("NodeExecution", back_populates="execution")


class NodeExecution(Base):
    """节点执行记录"""
    __tablename__ = "node_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    execution_id = Column(String(36), ForeignKey("flow_executions.id"), nullable=False)
    node_id = Column(String(36), nullable=False)
    node_name = Column(String(255))
    node_type = Column(String(50))
    host_id = Column(String(36), ForeignKey("hosts.id"))
    status = Column(String(20), default="pending")
    output = Column(Text)
    error = Column(Text)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    ansible_run_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    execution = relationship("FlowExecution", back_populates="node_executions")
    host = relationship("Host")


class ScheduledJob(Base):
    """定时任务"""
    __tablename__ = "scheduled_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    flow_id = Column(String(36), ForeignKey("flows.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)  # 添加描述字段
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    next_run_time = Column(DateTime(timezone=True))
    last_run_time = Column(DateTime(timezone=True))
    last_execution_id = Column(String(36), ForeignKey("flow_executions.id"))
    created_by = Column(String(36), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    flow = relationship("Flow", back_populates="scheduled_jobs")


class ExecutionLog(Base):
    """执行日志"""
    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    execution_id = Column(String(36), ForeignKey("flow_executions.id"), nullable=False)
    node_execution_id = Column(String(36), ForeignKey("node_executions.id"))
    level = Column(String(20))  # info, warning, error
    message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
