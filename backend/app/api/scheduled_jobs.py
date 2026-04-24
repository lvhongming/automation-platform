from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.core.utils import now
from app.models.flow import ScheduledJob, Flow
from app.models.user import User
from app.schemas.flow import ScheduledJobCreate, ScheduledJobUpdate, ScheduledJobResponse
from app.api.deps import get_current_user
from app.services.scheduler import task_scheduler

router = APIRouter(prefix="/scheduled-jobs", tags=["定时任务"])


@router.get("", response_model=dict)
async def list_scheduled_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    flow_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取定时任务列表"""
    query = select(ScheduledJob, Flow.name.label("flow_name")).outerjoin(Flow, ScheduledJob.flow_id == Flow.id)
    count_query = select(func.count(ScheduledJob.id))

    if flow_id:
        query = query.where(ScheduledJob.flow_id == flow_id)
        count_query = count_query.where(ScheduledJob.flow_id == flow_id)

    if enabled is not None:
        query = query.where(ScheduledJob.enabled == enabled)
        count_query = count_query.where(ScheduledJob.enabled == enabled)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(ScheduledJob.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        job = row[0]
        flow_name = row[1]
        item = ScheduledJobResponse.model_validate(job).model_dump()
        item["flow_name"] = flow_name
        items.append(item)

    return {"total": total, "items": items}


@router.get("/{job_id}", response_model=ScheduledJobResponse)
async def get_scheduled_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取定时任务详情"""
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    return ScheduledJobResponse.model_validate(job)


@router.post("", response_model=ScheduledJobResponse)
async def create_scheduled_job(
    job_data: ScheduledJobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建定时任务"""
    # 检查流程是否存在
    flow_result = await db.execute(select(Flow).where(Flow.id == job_data.flow_id))
    flow = flow_result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    # 验证 Cron 表达式
    try:
        from apscheduler.triggers.cron import CronTrigger
        CronTrigger.from_crontab(job_data.cron_expression)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 Cron 表达式")

    job = ScheduledJob(
        **job_data.model_dump(),
        created_by=current_user.id
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 添加到调度器
    task_scheduler.add_job(job)

    return ScheduledJobResponse.model_validate(job)


@router.put("/{job_id}", response_model=ScheduledJobResponse)
async def update_scheduled_job(
    job_id: str,
    job_data: ScheduledJobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新定时任务"""
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    # 验证 Cron 表达式
    if job_data.cron_expression:
        try:
            from apscheduler.triggers.cron import CronTrigger
            CronTrigger.from_crontab(job_data.cron_expression)
        except Exception:
            raise HTTPException(status_code=400, detail="无效的 Cron 表达式")

    for key, value in job_data.model_dump(exclude_unset=True).items():
        setattr(job, key, value)

    await db.commit()
    await db.refresh(job)

    # 更新调度器中的任务
    task_scheduler.remove_job(job_id)
    if job.enabled:
        task_scheduler.add_job(job)

    return ScheduledJobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_scheduled_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除定时任务"""
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    # 从调度器移除
    task_scheduler.remove_job(job_id)

    await db.delete(job)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{job_id}/toggle")
async def toggle_scheduled_job(
    job_id: str,
    enabled: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """启用/禁用定时任务"""
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    job.enabled = enabled
    await db.commit()

    # 更新调度器
    if enabled:
        task_scheduler.add_job(job)
    else:
        task_scheduler.pause_job(job_id)

    return {"message": "操作成功", "enabled": enabled}


@router.post("/{job_id}/trigger")
async def trigger_scheduled_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动触发定时任务"""
    result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="定时任务不存在")

    # 获取流程
    flow_result = await db.execute(select(Flow).where(Flow.id == job.flow_id))
    flow = flow_result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="关联的流程不存在")

    # 创建执行记录
    from app.models.flow import FlowExecution
    execution = FlowExecution(
        flow_id=flow.id,
        user_id=current_user.id,
        status="pending",
        trigger_type="manual",
        started_at=now()
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # 异步执行
    from app.main import execution_queue
    await execution_queue.put(str(execution.id))

    return {"execution_id": str(execution.id), "status": "pending"}
