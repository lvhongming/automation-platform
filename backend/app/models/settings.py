from sqlalchemy import Column, String, Boolean, Text, JSON
from app.db.database import Base


class SystemSettings(Base):
    """系统设置"""
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True, default="global")
    key = Column(String(100), unique=True, nullable=True, index=True)  # 允许 NULL

    # 基本设置
    system_name = Column(String(255), default="Ansible 自动化流程平台")
    system_description = Column(Text)
    timezone = Column(String(50), default="Asia/Shanghai")

    # 邮件设置
    email_enabled = Column(Boolean, default=False)
    smtp_host = Column(String(255))
    smtp_port = Column(String(10))
    smtp_username = Column(String(255))
    smtp_password = Column(String(255))
    smtp_from_email = Column(String(255))
    smtp_use_tls = Column(Boolean, default=True)

    # 企业微信
    wecom_enabled = Column(Boolean, default=False)
    wecom_webhook_url = Column(String(500))

    # 钉钉
    dingtalk_enabled = Column(Boolean, default=False)
    dingtalk_webhook_url = Column(String(500))

    # 执行设置
    default_timeout = Column(String(10), default="300")
    max_concurrency = Column(String(10), default="10")
    log_retention_days = Column(String(10), default="30")
    retry_count = Column(String(10), default="0")

    def to_dict(self):
        return {
            "basic": {
                "system_name": self.system_name or "Ansible 自动化流程平台",
                "description": self.system_description or "",
                "timezone": self.timezone or "Asia/Shanghai"
            },
            "email": {
                "enabled": self.email_enabled or False,
                "smtp_host": self.smtp_host or "",
                "smtp_port": int(self.smtp_port) if self.smtp_port else 465,
                "username": self.smtp_username or "",
                "password": self.smtp_password or "",
                "from_email": self.smtp_from_email or "",
                "use_tls": self.smtp_use_tls if self.smtp_use_tls is not None else True
            },
            "wecom": {
                "enabled": self.wecom_enabled or False,
                "webhook_url": self.wecom_webhook_url or ""
            },
            "dingtalk": {
                "enabled": self.dingtalk_enabled or False,
                "webhook_url": self.dingtalk_webhook_url or ""
            },
            "execution": {
                "default_timeout": int(self.default_timeout) if self.default_timeout else 300,
                "max_concurrency": int(self.max_concurrency) if self.max_concurrency else 10,
                "log_retention_days": int(self.log_retention_days) if self.log_retention_days else 30,
                "retry_count": int(self.retry_count) if self.retry_count else 0
            }
        }
