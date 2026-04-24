"""
常用工具函数
"""
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import json


def now() -> datetime:
    """获取当前本地时间（Asia/Shanghai 时区）"""
    return datetime.now(timezone(timedelta(hours=8)))


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """生成短 ID"""
    return uuid.uuid4().hex[:8]


def hash_password(password: str) -> str:
    """简单密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def format_duration(seconds: float) -> str:
    """格式化时长"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def parse_cron_expression(cron_expr: str) -> Dict[str, Any]:
    """解析 Cron 表达式"""
    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError("Cron 表达式必须包含5个部分")

    minute, hour, day, month, weekday = parts

    return {
        "minute": minute,
        "hour": hour,
        "day": day,
        "month": month,
        "weekday": weekday
    }


def format_cron_description(cron_expr: str) -> str:
    """生成 Cron 表达式的人类可读描述"""
    parts = parse_cron_expression(cron_expr)
    minute = parts["minute"]
    hour = parts["hour"]
    day = parts["day"]
    month = parts["month"]
    weekday = parts["weekday"]

    descriptions = []

    if day == "*" and month == "*" and weekday == "*":
        if hour != "*" and minute != "*":
            descriptions.append(f"每天 {hour}:{minute.zfill(2)}")
        else:
            descriptions.append("每分钟")
    elif weekday != "*":
        week_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        try:
            day_idx = int(weekday)
            descriptions.append(f"每周{week_names[day_idx]}")
        except:
            descriptions.append(f"每周{weekday}")
    elif day != "*":
        descriptions.append(f"每月{day}日")

    return " ".join(descriptions) or cron_expr


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def safe_json_loads(data: str, default: Any = None) -> Any:
    """安全的 JSON 解析"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """安全的 JSON 序列化"""
    try:
        return json.dumps(data)
    except (TypeError, ValueError):
        return default


def is_valid_ipv4(ip: str) -> bool:
    """验证 IPv4 地址"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def mask_sensitive_value(value: str, visible: int = 4) -> str:
    """遮蔽敏感值"""
    if not value or len(value) <= visible:
        return "*" * len(value) if value else ""
    return value[:visible] + "*" * (len(value) - visible)


def calculate_next_run(cron_expr: str, from_time: Optional[datetime] = None) -> datetime:
    """计算下次执行时间"""
    from apscheduler.triggers.cron import CronTrigger

    if from_time is None:
        from_time = datetime.now()

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
        return trigger.get_next_fire_time(None, from_time)
    except Exception:
        return None
