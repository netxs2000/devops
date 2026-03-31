"""通用工具函数模块。

提供项目中常用的数据处理、类型转换和时间解析工具。
旨在消除重复代码，统一处理逻辑。
"""

import logging
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)


def safe_int(value: Any, default: int = 0) -> int:
    """安全地将值转换为整数。

    Args:
        value: 待转换的值 (可以是字符串、数字等)
        default: 转换失败时的默认值，默认为 0

    Returns:
        转换后的整数
    """
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default


def safe_id(value: Any) -> str | None:
    """将外部 API 返回的 ID 安全转换为字符串，过滤零值和空值。

    用于防御外部系统返回的 ID 类型不确定性 (int/str/dict 混合)。
    遵循 contexts.md §19.1 "永远不信任外部输入" 守则。

    Args:
        value: 外部 API 返回的原始 ID (可能是 int, str, None, dict 等)。

    Returns:
        安全的字符串 ID，若为无效值则返回 None。

    Examples:
        >>> safe_id(123)       -> "123"
        >>> safe_id("456")     -> "456"
        >>> safe_id(0)         -> None  (禅道零值语义)
        >>> safe_id("0")       -> None
        >>> safe_id("")        -> None
        >>> safe_id(None)      -> None
    """
    if value is None:
        return None
    if isinstance(value, dict):
        # 部分 API 返回 {"id": 123, "name": "xxx"} 而非裸值
        value = value.get("id", value.get("account"))
        if value is None:
            return None
    s = str(value).strip()
    if s in ("", "0", "None", "null"):
        return None
    return s


def safe_float(value: Any, default: float = 0.0) -> float:
    """安全地将值转换为浮点数。

    Args:
        value: 待转换的值
        default: 转换失败时的默认值，默认为 0.0

    Returns:
        转换后的浮点数
    """
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def parse_iso8601(date_str: str | None) -> datetime | None:
    """解析 ISO 8601 格式的时间字符串。

    统一处理带 'Z' 后缀的 UTC 时间字符串，将其转换为带时区信息的 datetime 对象。

    Args:
        date_str: ISO 8601 格式的时间字符串 (如 '2023-01-01T12:00:00Z')

    Returns:
        datetime 对象 (带时区信息)，如果解析失败或输入为空则返回 None
    """
    if not date_str:
        return None
    try:
        cleaned_str = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned_str)
    except ValueError as e:
        logger.warning(f"Failed to parse date string '{date_str}': {e}")
        return None


from pathlib import Path

from devops_collector.config import settings


def resolve_data_path(filename: str) -> Path:
    """获取数据文件的绝对持久化路径。

    自动确保父目录存在。

    Args:
        filename: 文件名 (如 'users.json')

    Returns:
        Path: 完整的绝对路径
    """
    data_dir = Path(settings.storage.data_dir)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create data directory {data_dir}: {e}")
    return data_dir / filename
