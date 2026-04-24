from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.core.utils import now
from app.models.flow import FlowExecution, Flow
from app.models.host import Host
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["控制台"])


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取控制台统计数据"""
    today = now().date()
    today_start = datetime.combine(today, datetime.min.time())

    # 流程总数
    flow_count = await db.execute(select(func.count(Flow.id)))
    total_flows = flow_count.scalar() or 0

    # 主机总数
    host_count = await db.execute(select(func.count(Host.id)))
    total_hosts = host_count.scalar() or 0

    # 今日执行次数
    today_exec_count = await db.execute(
        select(func.count(FlowExecution.id))
        .where(FlowExecution.created_at >= today_start)
    )
    today_executions = today_exec_count.scalar() or 0

    # 失败执行次数（最近7天）
    week_ago = now() - timedelta(days=7)
    failed_count = await db.execute(
        select(func.count(FlowExecution.id))
        .where(FlowExecution.status == "failed")
        .where(FlowExecution.created_at >= week_ago)
    )
    recent_failed = failed_count.scalar() or 0

    return {
        "flows": total_flows,
        "hosts": total_hosts,
        "executions": today_executions,
        "failed": recent_failed
    }


@router.get("/recent-executions")
async def get_recent_executions(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取最近执行记录"""
    query = (
        select(FlowExecution, Flow.name.label("flow_name"))
        .outerjoin(Flow, FlowExecution.flow_id == Flow.id)
        .order_by(FlowExecution.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        execution = row[0]
        flow_name = row[1]
        items.append({
            "id": execution.id,
            "flow_id": execution.flow_id,
            "flow_name": flow_name,
            "status": execution.status,
            "trigger_type": execution.trigger_type,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
            "user": None  # 需要关联查询 user 表
        })

    return {"items": items}
