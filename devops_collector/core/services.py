# -*- coding: utf-8 -*-
"""devops_collector.core.services

业务服务层公共工具，提供 SCD Type2（慢变维）更新的统一实现。

本文件遵循 **Google Python Style Guide**，所有注释采用中文的 Google Docstring 风格。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Type

from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

# 项目模型基类（所有模型均继承自 Base）
from devops_collector.models.base_models import Base

log = logging.getLogger(__name__)


class ConcurrencyError(RuntimeError):
    """乐观锁冲突异常。

    当更新时发现记录已被其他事务修改（sync_version 不匹配）或
    未能找到当前有效记录时抛出。业务层可捕获后决定重试或返回错误信息。
    """


def close_current_and_insert_new(
    session: Session,
    model_cls: Type[Base],
    natural_key: Dict[str, Any],
    new_data: Dict[str, Any],
) -> Base:
    """统一的 SCD Type2 更新函数。

    该函数在同一个事务中完成以下步骤：

    1. 根据 ``natural_key``（业务唯一键）查询当前有效记录（``is_current=True``）。
       若未找到则抛出 ``ConcurrencyError``。
    2. 检查 ``sync_version`` 是否与 ``new_data`` 中提供的 ``sync_version`` 相同（乐观锁）。
       不匹配则抛出 ``ConcurrencyError``。
    3. 将当前记录标记为失效：``is_current=False``、``effective_to=now()``。
    4. 基于 ``natural_key`` 与 ``new_data`` 创建一条新记录：
       - ``sync_version`` + 1
       - ``effective_from=now()``
       - ``is_current=True``
       - 其它业务字段使用 ``new_data`` 中的值（若未提供则保留原值）。
    5. 提交事务并返回新创建的对象。

    参数:
        session: 已打开的 SQLAlchemy ``Session``（事务会话）。
        model_cls: 需要更新的模型类，例如 ``Organization``、``User``。
        natural_key: 业务唯一键的字典，例如 ``{"org_id": "ORG_001"}``。
        new_data: 需要写入的新字段字典，**必须包含** ``sync_version`` 键，
                  其值为当前记录的 ``sync_version``（用于乐观锁校验）。

    返回:
        新插入的模型实例（已持久化）。

    Raises:
        ConcurrencyError: 当记录不存在或乐观锁冲突时抛出。
    """
    # 1️⃣ 查询当前有效记录
    try:
        current = (
            session.query(model_cls)
            .filter_by(**natural_key, is_current=True)
            .one()
        )
    except NoResultFound as exc:
        raise ConcurrencyError(
            f"未找到 {model_cls.__name__}（键 {natural_key}）的当前有效记录"
        ) from exc

    # 2️⃣ 乐观锁校验
    expected_version = new_data.get("sync_version")
    if expected_version is None:
        raise ConcurrencyError("new_data 必须包含 sync_version 用于乐观锁校验")
    if current.sync_version != expected_version:
        raise ConcurrencyError(
            f"乐观锁冲突：当前版本 {current.sync_version} 与期望 {expected_version} 不匹配"
        )

    # 3️⃣ 关闭当前记录
    now = datetime.now(timezone.utc)
    current.is_current = False
    current.effective_to = now
    session.add(current)

    # 4️⃣ 构造新记录
    # 复制业务自然键，合并新字段（去掉 sync_version 防止误写入）
    insert_kwargs: Dict[str, Any] = {**natural_key}
    new_data_clean = {k: v for k, v in new_data.items() if k != "sync_version"}
    insert_kwargs.update(new_data_clean)
    insert_kwargs.update(
        {
            "sync_version": current.sync_version + 1,
            "effective_from": now,
            "effective_to": None,
            "is_current": True,
            "is_deleted": False,
        }
    )

    new_obj = model_cls(**insert_kwargs)
    session.add(new_obj)

    # 5️⃣ 提交（由调用方决定 commit）
    session.flush()  # 确保新对象获取主键 ID
    log.info(
        "SCD Type2 更新 %s: %s -> %s (version %s→%s)",
        model_cls.__name__,
        natural_key,
        insert_kwargs,
        current.sync_version,
        new_obj.sync_version,
    )
    return new_obj
