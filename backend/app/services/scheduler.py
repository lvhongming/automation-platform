"""
定时任务调度器
基于 APScheduler 实现
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import asyncio

from app.models.flow import Flow, FlowExecution, ScheduledJob
from app.core.utils import now
from app.services.executor import AnsibleExecutor


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_session_maker = None

    def init(self, db_session_maker):
        """初始化调度器"""
        self.db_session_maker = db_session_maker

    async def load_jobs_from_db(self):
        """从数据库加载定时任务"""
        if not self.db_session_maker:
            return

        async with self.db_session_maker() as db:
            result = await db.execute(
                select(ScheduledJob).where(ScheduledJob.enabled == True)
            )
            jobs = result.scalars().all()

            for job in jobs:
                self.add_job(job)

    def add_job(self, scheduled_job: ScheduledJob):
        """添加定时任务"""
        try:
            trigger = CronTrigger.from_crontab(scheduled_job.cron_expression)

            self.scheduler.add_job(
                self._execute_scheduled_job,
                trigger=trigger,
                args=[scheduled_job.id],
                id=str(scheduled_job.id),
                replace_existing=True,
                name=scheduled_job.name
            )
        except Exception as e:
            print(f"Failed to add job {scheduled_job.id}: {e}")

    def remove_job(self, job_id: str):
        """移除定时任务"""
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    def pause_job(self, job_id: str):
        """暂停定时任务"""
        try:
            self.scheduler.pause_job(job_id)
        except Exception:
            pass

    def resume_job(self, job_id: str):
        """恢复定时任务"""
        try:
            self.scheduler.resume_job(job_id)
        except Exception:
            pass

    async def _execute_scheduled_job(self, scheduled_job_id: str):
        """执行定时任务"""
        if not self.db_session_maker:
            return

        async with self.db_session_maker() as db:
            # 获取定时任务
            result = await db.execute(
                select(ScheduledJob).where(ScheduledJob.id == scheduled_job_id)
            )
            scheduled_job = result.scalar_one_or_none()

            if not scheduled_job or not scheduled_job.enabled:
                return

            # 获取流程
            flow_result = await db.execute(
                select(Flow).where(Flow.id == scheduled_job.flow_id)
            )
            flow = flow_result.scalar_one_or_none()

            if not flow:
                return

            # 创建执行记录
            execution = FlowExecution(
                flow_id=flow.id,
                status="pending",
                trigger_type="scheduled",
                started_at=now(),
                execution_data={"scheduled_job_id": scheduled_job_id}
            )
            db.add(execution)
            await db.commit()
            await db.refresh(execution)

            # 更新定时任务最后执行时间
            scheduled_job.last_run_time = now()
            scheduled_job.last_execution_id = execution.id

            # 计算下次执行时间
            job = self.scheduler.get_job(str(scheduled_job_id))
            if job:
                scheduled_job.next_run_time = job.next_run_time

            await db.commit()

            # 执行流程（设置 ws_manager 以支持实时日志）
            from app.services.websocket import manager as ws_manager
            executor = AnsibleExecutor(db)
            executor.set_ws_manager(ws_manager)
            await executor.execute_flow(execution.id)

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("Task scheduler started")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Task scheduler shutdown")


# 全局调度器实例
task_scheduler = TaskScheduler()
