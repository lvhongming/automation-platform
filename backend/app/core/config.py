from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import secrets
import os


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    # 项目信息
    PROJECT_NAME: str = "Ansible 自动化流程平台"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/automation_platform"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT - 使用固定密钥，支持环境变量覆盖
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "automation-platform-secret-key-change-in-production-2024")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Ansible
    ANSIBLE_PLAYBOOKS_DIR: str = "/data/automation-platform/backend/playbooks"
    ANSIBLE_INVENTORY_DIR: str = "/data/automation-platform/backend/inventory"
    ANSIBLE_TIMEOUT: int = 300

    # 文件上传
    UPLOAD_DIR: str = "/data/automation-platform/backend/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB


settings = Settings()
