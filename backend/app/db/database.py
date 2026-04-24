from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _get_engine_kwargs():
    """根据数据库类型获取引擎参数"""
    kwargs = {"echo": settings.DEBUG}
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs.update({
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20
        })
    return kwargs


engine = create_async_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs()
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
