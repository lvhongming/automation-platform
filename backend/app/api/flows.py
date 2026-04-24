from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import json

from app.db.database import get_db
from app.core.utils import now
from app.models.flow import Flow, FlowExecution, NodeExecution
from app.models.user import User, UserFlowPermission
from app.schemas.flow import (
    FlowResponse, FlowCreate, FlowUpdate, FlowDesignUpdate, FlowDetailResponse,
    FlowExecutionResponse, FlowExecutionCreate
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/flows", tags=["流程管理"])


@router.get("", response_model=dict)
async def list_flows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取流程列表"""
    query = select(Flow)
    count_query = select(func.count(Flow.id))

    if status:
        query = query.where(Flow.status == status)
        count_query = count_query.where(Flow.status == status)

    if keyword:
        query = query.where(
            or_(
                Flow.name.contains(keyword),
                Flow.description.contains(keyword)
            )
        )
        count_query = count_query.where(
            or_(
                Flow.name.contains(keyword),
                Flow.description.contains(keyword)
            )
        )

    # 非管理员只能看到自己的流程
    # if not current_user.role or current_user.role.name != 'admin':
    #     query = query.where(Flow.owner_id == current_user.id)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页查询
    query = query.order_by(Flow.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    flows = result.scalars().all()

    return {"total": total, "items": [FlowResponse.model_validate(f) for f in flows]}


@router.get("/{flow_id}", response_model=FlowDetailResponse)
async def get_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取流程详情"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    return FlowDetailResponse.model_validate(flow)


@router.post("", response_model=FlowResponse)
async def create_flow(
    flow_data: FlowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建流程"""
    flow = Flow(
        **flow_data.model_dump(),
        owner_id=current_user.id
    )
    db.add(flow)
    await db.commit()
    await db.refresh(flow)
    return FlowResponse.model_validate(flow)


@router.put("/{flow_id}", response_model=FlowResponse)
async def update_flow(
    flow_id: str,
    flow_data: FlowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 检查权限
    if flow.owner_id != current_user.id:
        # TODO: 检查是否有编辑权限
        pass

    for key, value in flow_data.model_dump(exclude_unset=True).items():
        setattr(flow, key, value)

    await db.commit()
    await db.refresh(flow)
    return FlowResponse.model_validate(flow)


@router.put("/{flow_id}/design", response_model=FlowResponse)
async def save_flow_design(
    flow_id: str,
    design_data: FlowDesignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """保存流程设计（节点和连线）"""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"接收到的设计数据: {design_data}")

    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 更新名称（如果提供）
    if design_data.name is not None:
        flow.name = design_data.name
        logger.info(f"更新流程名称为: {design_data.name}")
    # 更新流程数据（如果提供）
    if design_data.flow_data is not None:
        flow.flow_data = design_data.flow_data
    # 更新变量（如果提供）
    if design_data.variables is not None:
        flow.variables = design_data.variables

    await db.commit()
    await db.refresh(flow)
    return FlowResponse.model_validate(flow)


@router.delete("/{flow_id}")
async def delete_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除流程"""
    try:
        result = await db.execute(select(Flow).where(Flow.id == flow_id))
        flow = result.scalar_one_or_none()

        if not flow:
            raise HTTPException(status_code=404, detail="流程不存在")

        # 检查权限：管理员或流程所有者可以删除
        # 直接比较 role_id 是否为 admin 角色的 id
        from app.models.user import Role
        role_result = await db.execute(select(Role).where(Role.name == 'admin'))
        admin_role = role_result.scalar_one_or_none()
        if flow.owner_id != current_user.id and current_user.role_id != admin_role.id:
            raise HTTPException(status_code=403, detail="无权限删除")

        # 先删除关联的执行记录
        from app.models.flow import FlowExecution, NodeExecution, ExecutionLog, ScheduledJob
        from app.models.user import UserFlowPermission
        from sqlalchemy import delete
        
        # 获取所有执行记录ID
        exec_result = await db.execute(select(FlowExecution.id).where(FlowExecution.flow_id == flow_id))
        execution_ids = [row[0] for row in exec_result.fetchall()]
        
        # 批量删除执行记录关联的数据（注意删除顺序：先子表后主表）
        if execution_ids:
            # 1. 先删除执行日志
            await db.execute(delete(ExecutionLog).where(ExecutionLog.execution_id.in_(execution_ids)))
            # 2. 再删除节点执行记录
            await db.execute(delete(NodeExecution).where(NodeExecution.execution_id.in_(execution_ids)))
            # 3. 最后删除执行记录
            await db.execute(delete(FlowExecution).where(FlowExecution.flow_id == flow_id))
        
        # 删除关联的定时任务
        await db.execute(delete(ScheduledJob).where(ScheduledJob.flow_id == flow_id))
        
        # 删除关联的权限
        await db.execute(delete(UserFlowPermission).where(UserFlowPermission.flow_id == flow_id))
        
        # 最后删除流程
        await db.execute(delete(Flow).where(Flow.id == flow_id))
        await db.commit()
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] 删除流程失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{flow_id}/validate")
async def validate_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """校验流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    flow_data = flow.flow_data or {}
    nodes = flow_data.get("nodes", [])
    edges = flow_data.get("edges", [])

    errors = []

    # 检查是否有节点
    if not nodes:
        errors.append("流程至少需要一个节点")

    # 检查节点是否配置完整
    for node in nodes:
        if node.get("type") not in ["comment"]:
            config = node.get("data", {}).get("config", {})
            if not config.get("command") and not config.get("script_content"):
                errors.append(f"节点 '{node.get('data', {}).get('label', node.get('id'))}' 未配置命令或脚本")

    # 检查连线
    if len(nodes) > 1 and len(edges) == 0:
        errors.append("多个节点需要连线来定义执行顺序")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "message": "流程校验通过"}


@router.post("/{flow_id}/publish", response_model=FlowResponse)
async def publish_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发布流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    flow.status = "published"
    await db.commit()
    await db.refresh(flow)
    return FlowResponse.model_validate(flow)


@router.post("/{flow_id}/copy", response_model=FlowResponse)
async def copy_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """复制流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 创建新流程，复制的名称
    new_flow = Flow(
        name=f"{flow.name} (副本)",
        description=flow.description,
        flow_data=flow.flow_data,
        variables=flow.variables,
        status="draft",  # 复制后默认为草稿状态
        owner_id=current_user.id
    )
    db.add(new_flow)
    await db.commit()
    await db.refresh(new_flow)
    return FlowResponse.model_validate(new_flow)


@router.post("/{flow_id}/unpublish", response_model=FlowResponse)
async def unpublish_flow(
    flow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消发布流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    flow.status = "draft"
    await db.commit()
    await db.refresh(flow)
    return FlowResponse.model_validate(flow)


@router.post("/{flow_id}/execute", response_model=dict)
async def execute_flow(
    flow_id: str,
    exec_data: FlowExecutionCreate = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """执行流程"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 获取节点数据（兼容嵌套结构）
    # 处理可能是 JSON 字符串的情况
    raw_flow_data = flow.flow_data
    if isinstance(raw_flow_data, str):
        try:
            flow_data = json.loads(raw_flow_data)
        except json.JSONDecodeError:
            flow_data = {}
    else:
        flow_data = raw_flow_data or {}
    
    # 兼容前端保存的嵌套结构 flow_data.flow_data.nodes
    if isinstance(flow_data, dict) and "flow_data" in flow_data:
        nodes = flow_data.get("flow_data", {}).get("nodes", [])
    elif isinstance(flow_data, dict):
        nodes = flow_data.get("nodes", [])
    else:
        nodes = []

    # 检查流程数据是否存在
    if not flow.flow_data or not nodes:
        raise HTTPException(status_code=400, detail="流程没有节点，请先添加节点")

    # 检查是否有可执行的节点
    executable_nodes = [n for n in nodes if n.get("type") not in ["comment", "notify"]]
    if not executable_nodes:
        raise HTTPException(status_code=400, detail="流程没有可执行的节点")

    # 创建执行记录
    trigger_type = "manual"
    if flow.status != "published":
        trigger_type = "test"  # 草稿状态执行为测试模式

    execution = FlowExecution(
        flow_id=flow_id,
        user_id=current_user.id,
        status="pending",
        trigger_type=trigger_type,
        started_at=now(),
        execution_data={
            "host_ids": exec_data.host_ids if exec_data else None,
            "variables": exec_data.variables if exec_data and exec_data.variables else {}
        }
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 加入执行队列（异步执行）
    from app.main import execution_queue
    await execution_queue.put(str(execution.id))
    print(f"[API] Execution {execution.id} added to queue")

    return {"execution_id": str(execution.id), "status": "pending"}


@router.post("/{flow_id}/permissions")
async def set_flow_permissions(
    flow_id: str,
    permissions: List[dict],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置流程权限"""
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 删除现有权限
    await db.execute(
        UserFlowPermission.__table__.delete().where(
            UserFlowPermission.flow_id == flow_id
        )
    )

    # 创建新权限
    for perm in permissions:
        user_flow_perm = UserFlowPermission(
            user_id=perm["user_id"],
            flow_id=flow_id,
            actions=perm.get("actions", ["view", "execute"])
        )
        db.add(user_flow_perm)

    await db.commit()
    return {"message": "权限设置成功"}
