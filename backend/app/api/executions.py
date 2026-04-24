from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.core.utils import now
from app.models.flow import FlowExecution, NodeExecution, ExecutionLog, Flow
from app.models.user import User
from app.schemas.flow import FlowExecutionResponse, NodeExecutionResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/executions", tags=["执行记录"])


@router.get("", response_model=dict)
async def list_executions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    flow_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取执行历史"""
    # 使用 left join 获取 flow_name
    query = select(FlowExecution, Flow.name.label("flow_name")).outerjoin(Flow, FlowExecution.flow_id == Flow.id)
    count_query = select(func.count(FlowExecution.id))

    if flow_id:
        query = query.where(FlowExecution.flow_id == flow_id)
        count_query = count_query.where(FlowExecution.flow_id == flow_id)

    if status:
        query = query.where(FlowExecution.status == status)
        count_query = count_query.where(FlowExecution.status == status)

    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.where(FlowExecution.created_at >= start)
        count_query = count_query.where(FlowExecution.created_at >= start)

    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.where(FlowExecution.created_at <= end)
        count_query = count_query.where(FlowExecution.created_at <= end)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    query = query.order_by(FlowExecution.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    # 构建响应数据
    items = []
    for row in rows:
        execution = row[0]  # FlowExecution
        flow_name = row[1]   # flow_name from join
        item_dict = {
            "id": execution.id,
            "flow_id": execution.flow_id,
            "flow_name": flow_name,
            "user_id": execution.user_id,
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "started_at": execution.started_at,
            "finished_at": execution.finished_at,
            "result_summary": execution.result_summary or {},
            "created_at": execution.created_at
        }
        items.append(FlowExecutionResponse.model_validate(item_dict))

    return {"total": total, "items": items}


@router.get("/{execution_id}", response_model=dict)
async def get_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取执行详情"""
    result = await db.execute(
        select(FlowExecution, Flow.name.label("flow_name"))
        .outerjoin(Flow, FlowExecution.flow_id == Flow.id)
        .where(FlowExecution.id == execution_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    execution = row[0]
    flow_name = row[1]

    return {
        "id": execution.id,
        "flow_id": execution.flow_id,
        "flow_name": flow_name,
        "user_id": execution.user_id,
        "status": execution.status,
        "trigger_type": execution.trigger_type,
        "started_at": execution.started_at,
        "finished_at": execution.finished_at,
        "result_summary": execution.result_summary or {},
        "created_at": execution.created_at
    }


@router.get("/{execution_id}/nodes", response_model=list[NodeExecutionResponse])
async def get_execution_nodes(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取执行节点列表"""
    result = await db.execute(
        select(NodeExecution)
        .where(NodeExecution.execution_id == execution_id)
        .order_by(NodeExecution.created_at)
    )
    nodes = result.scalars().all()
    return [NodeExecutionResponse.model_validate(n) for n in nodes]


@router.get("/{execution_id}/nodes/{node_execution_id}/logs")
async def get_node_execution_logs(
    execution_id: str,
    node_execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取节点执行日志"""
    # 从数据库获取日志
    result = await db.execute(
        select(ExecutionLog)
        .where(ExecutionLog.node_execution_id == node_execution_id)
        .order_by(ExecutionLog.created_at)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "level": log.level,
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


@router.post("/{execution_id}/stop")
async def stop_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """停止执行"""
    result = await db.execute(
        select(FlowExecution).where(FlowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    if execution.status not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail="执行已结束，无法停止")

    execution.status = "stopped"
    execution.finished_at = now()
    await db.commit()

    # TODO: 停止正在运行的 Ansible 任务

    return {"message": "停止成功"}


@router.post("/{execution_id}/retry")
async def retry_execution(
    execution_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重试执行"""
    result = await db.execute(
        select(FlowExecution).where(FlowExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()

    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")

    # 创建新的执行记录
    new_execution = FlowExecution(
        flow_id=execution.flow_id,
        user_id=current_user.id,
        status="pending",
        trigger_type="manual",
        started_at=now(),
        execution_data=execution.execution_data
    )
    db.add(new_execution)
    await db.commit()
    await db.refresh(new_execution)

    # 异步执行（设置 ws_manager 以支持实时日志）
    from app.services.executor import AnsibleExecutor
    from app.services.websocket import manager as ws_manager
    executor = AnsibleExecutor(db)
    executor.set_ws_manager(ws_manager)
    await executor.execute_flow(new_execution.id)

    return {"execution_id": str(new_execution.id), "status": "pending"}
