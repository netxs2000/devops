"""TODO: Add module description."""

from typing import Any


EXECUTION_HISTORY: dict[int, list[Any]] = {}
RECENT_PROJECTS: set = set()
PIPELINE_STATUS: dict[int, dict[str, Any]] = {}
GLOBAL_QUALITY_ALERTS: list[dict[str, Any]] = []
NOTIFICATION_QUEUES: dict[str, list[Any]] = {}
