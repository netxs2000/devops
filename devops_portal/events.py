# -*- coding: utf-8 -*-
"""Events & Notifications Module.

Handles SSE notifications and real-time event dispatching.
"""
import json
import logging
import asyncio
from datetime import datetime
from typing import Union, List, Dict, Any, Optional
from devops_portal.state import NOTIFICATION_QUEUES

logger = logging.getLogger(__name__)

async def push_notification(
    user_ids: Union[str, List[str]], 
    message: str, 
    type: str = 'info',
    metadata: Optional[Dict[str, Any]] = None
):
    """推送通知到 SSE（支持单播/多播/广播）。
    
    Args:
        user_ids: 接收者ID（单个str或List，特殊值 "ALL" 表示全员广播）
        message: 通知消息内容
        type: 通知类型 (info/success/warning/error)
        metadata: 附加元数据（如关联的 issue_id, project_id 等）
    """
    # 解析目标用户列表
    if isinstance(user_ids, str):
        if user_ids == "ALL":
            # 全员广播：推送给所有在线用户
            target_users = list(NOTIFICATION_QUEUES.keys())
            logger.info(f"Broadcasting notification to all {len(target_users)} connected users")
        else:
            target_users = [user_ids]
    else:
        target_users = user_ids
    
    # 构建通知数据（包含时间戳和元数据）
    data = json.dumps({
        "message": message, 
        "type": type,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat()
    })
    
    # 推送到目标用户的所有连接
    success_count = 0
    total_queues = 0
    
    for user_id in target_users:
        if user_id in NOTIFICATION_QUEUES:
            for q in NOTIFICATION_QUEUES[user_id]:
                total_queues += 1
                try:
                    await q.put(data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to push notification to user {user_id}: {e}")
        else:
            logger.debug(f"User {user_id} not connected to SSE stream, skipping")
    
    if total_queues > 0:
        logger.info(f"Notification result: {success_count}/{total_queues} queues successful (Targets: {len(target_users)} users)")
