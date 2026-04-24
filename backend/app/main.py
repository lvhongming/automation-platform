from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import traceback

from app.core.config import settings
from app.db.database import init_db, async_session_maker
from app.api import auth, hosts, flows, executions, websocket, templates, scheduled_jobs, dashboard, users, roles
from app.api.syssettings import router as settings_router
from app.services.scheduler import task_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    await init_db()

    # 启动定时任务调度器
    task_scheduler.init(async_session_maker)
    await task_scheduler.load_jobs_from_db()
    task_scheduler.start()

    # 启动后台任务处理（用于异步执行流程）
    asyncio.create_task(process_execution_queue())

    yield

    # 关闭时
    task_scheduler.shutdown()


# 简单的执行队列（生产环境应使用 Redis 队列）
execution_queue = asyncio.Queue()


async def process_execution_queue():
    """处理执行队列"""
    from app.services.executor import AnsibleExecutor
    from app.db.database import async_session_maker
    from app.services.websocket import manager as ws_manager

    while True:
        try:
            execution_id = await execution_queue.get()
            print(f"[Executor] Starting execution: {execution_id}")
            try:
                async with async_session_maker() as db:
                    executor = AnsibleExecutor(db)
                    executor.set_ws_manager(ws_manager)  # 设置 WebSocket manager
                    await executor.execute_flow(execution_id)
                print(f"[Executor] Completed execution: {execution_id}")
            except Exception as e:
                print(f"[Executor] Error in execution {execution_id}: {e}")
                traceback.print_exc()
            execution_queue.task_done()
        except asyncio.CancelledError:
            print("[Executor] Queue processing cancelled")
            break
        except Exception as e:
            print(f"[Executor] Queue error: {e}")
            traceback.print_exc()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(hosts.router, prefix="/api")
app.include_router(flows.router, prefix="/api")
app.include_router(executions.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(scheduled_jobs.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(roles.router, prefix="/api")
app.include_router(settings_router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
