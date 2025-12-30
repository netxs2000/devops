from typing import Dict, List, Any

# Global In-Memory State
EXECUTION_HISTORY: Dict[int, List[Any]] = {}
RECENT_PROJECTS: set = set()
PIPELINE_STATUS: Dict[int, Dict[str, Any]] = {}
GLOBAL_QUALITY_ALERTS: List[Dict[str, Any]] = []

# SSE Notification Queues: {user_id: [Queue]}
NOTIFICATION_QUEUES: Dict[str, List[Any]] = {}
