from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.models.settings import SystemSettings


router = APIRouter(prefix="/api/settings", tags=["设置"])


class BasicSettings(BaseModel):
    system_name: str = "Ansible 自动化流程平台"
    description: Optional[str] = ""
    timezone: str = "Asia/Shanghai"


class EmailSettings(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 465
    username: str = ""
    password: str = ""
    from_email: str = ""
    use_tls: bool = True


class WeComSettings(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class DingTalkSettings(BaseModel):
    enabled: bool = False
    webhook_url: str = ""


class ExecutionSettings(BaseModel):
    default_timeout: int = 300
    max_concurrency: int = 10
    log_retention_days: int = 30
    retry_count: int = 0


class SettingsUpdate(BaseModel):
    basic: Optional[BasicSettings] = None
    email: Optional[EmailSettings] = None
    wecom: Optional[WeComSettings] = None
    dingtalk: Optional[DingTalkSettings] = None
    execution: Optional[ExecutionSettings] = None


async def get_or_create_settings(db: AsyncSession) -> SystemSettings:
    """获取或创建设置记录"""
    result = await db.execute(select(SystemSettings).where(SystemSettings.id == "global"))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SystemSettings(id="global")
        db.add(settings)
        await db.flush()
    return settings


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    """获取所有设置"""
    settings = await get_or_create_settings(db)
    return settings.to_dict()


@router.put("")
async def update_settings(data: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    """更新设置"""
    settings = await get_or_create_settings(db)

    if data.basic:
        settings.system_name = data.basic.system_name
        settings.system_description = data.basic.description
        settings.timezone = data.basic.timezone

    if data.email:
        settings.email_enabled = data.email.enabled
        settings.smtp_host = data.email.smtp_host
        settings.smtp_port = str(data.email.smtp_port)
        settings.smtp_username = data.email.username
        settings.smtp_password = data.email.password
        settings.smtp_from_email = data.email.from_email
        settings.smtp_use_tls = data.email.use_tls

    if data.wecom:
        settings.wecom_enabled = data.wecom.enabled
        settings.wecom_webhook_url = data.wecom.webhook_url

    if data.dingtalk:
        settings.dingtalk_enabled = data.dingtalk.enabled
        settings.dingtalk_webhook_url = data.dingtalk.webhook_url

    if data.execution:
        settings.default_timeout = str(data.execution.default_timeout)
        settings.max_concurrency = str(data.execution.max_concurrency)
        settings.log_retention_days = str(data.execution.log_retention_days)
        settings.retry_count = str(data.execution.retry_count)

    await db.commit()
    return {"message": "设置保存成功"}
