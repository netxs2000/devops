# P2 任务实施方案：完善实时通知 (SSE) 的定向推送逻辑

## 📋 任务概述

**当前问题**:
1. `push_notification` 在质量门禁拦截时使用 `"GLOBAL_BROADCAST"` 占位符
2. 无法精准推送给特定干系人（如项目负责人、需求评审人、Bug经办人）

**目标**:
1. 实现基于业务场景的接收者解析逻辑
2. 支持单播、多播、广播三种推送模式
3. 添加推送失败处理和日志记录

---

## 🎯 实施计划

### 阶段1: 增强 push_notification 函数

**改进点**:
- 支持单个用户ID (`str`) 或用户ID列表 (`List[str]`)
- 支持 `"ALL"` 关键字实现全员广播
- 添加推送失败时的日志记录

**代码示例**:
```python
async def push_notification(
    user_ids: Union[str, List[str]], 
    message: str, 
    type: str = 'info',
    metadata: Optional[Dict] = None
):
    \"\"\"推送通知到 SSE（支持单播/多播/广播）。
    
    Args:
        user_ids: 接收者ID（单个str或List，特殊值 "ALL" 表示广播）
        message: 通知消息内容
        type: 通知类型 (info/success/warning/error)
        metadata: 附加元数据（如关联的 issue_id, project_id 等）
    \"\"\"
    if isinstance(user_ids, str):
        if user_ids == "ALL":
            # 全员广播
            target_users = list(NOTIFICATION_QUEUES.keys())
        else:
            target_users = [user_ids]
    else:
        target_users = user_ids
    
    data = json.dumps({
        "message": message, 
        "type": type,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat()
    })
    
    success_count = 0
    for user_id in target_users:
        if user_id in NOTIFICATION_QUEUES:
            for q in NOTIFICATION_QUEUES[user_id]:
                try:
                    await q.put(data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to push notification to user {user_id}: {e}")
        else:
            logger.debug(f"User {user_id} not connected to SSE stream, skipping notification")
    
    logger.info(f"Pushed notification to {success_count} queues (target: {len(target_users)} users)")
```

---

### 阶段2: 实现接收者解析逻辑

#### 2.1 质量门禁拦截场景

**业务场景**: 质量门禁检查失败时，通知项目负责人

**实现方式**: 
1. 从 Project 表查询 `product_manager_id`, `test_manager_id`
2. 如果未配置，则通知全员

**代码位置**: `get_quality_gate` 函数（约第426行）

**改进代码**:
```python
if not is_all_passed:
    # 查询项目负责人
    notify_users = await get_project_stakeholders(project_id)
    if not notify_users:
        notify_users = "ALL"  # 兜底：全员广播
    
    asyncio.create_task(push_notification(
        notify_users,
        f"🚨 项目 {project_id} 质量门禁拦截: {summary}",
        "warning",
        metadata={"project_id": project_id, "gate_status": "blocked"}
    ))
```

---

#### 2.2 测试用例执行失败场景

**业务场景**: 测试用例执行失败时，通知用例创建者和需求负责人

**代码位置**: `execute_test_case` 函数（约第754行）

**改进代码**:
```python
if final_result == "failed":
    # 通知相关人员
    notify_users = []
    
    # 1. 通知用例创建者
    tc_author_id = getattr(tc_obj, 'author_id', None)
    if tc_author_id:
        notify_users.append(str(tc_author_id))
    
    # 2. 如果关联了需求，通知需求负责人
    if tc_obj.requirement_id:
        req_author = await get_requirement_author(project_id, tc_obj.requirement_id)
        if req_author:
            notify_users.append(str(req_author))
    
    if notify_users:
        asyncio.create_task(push_notification(
            notify_users,
            f"⚠️ 测试用例 #{issue_iid} 执行失败: {tc_obj.title}",
            "error",
            metadata={"issue_iid": issue_iid, "project_id": project_id}
        ))
```

---

#### 2.3 需求评审状态变更场景

**业务场景**: 需求评审状态变更时，通知需求提出者

**代码位置**: 需要在 `update_requirement_review_state` 端点中添加

**代码示例**:
```python
@app.post("/projects/{project_id}/requirements/{req_iid}/review")
async def update_requirement_review_state(
    project_id: int, 
    req_iid: int, 
    new_state: str,
    current_user = Depends(get_current_user)
):
    # ... 更新逻辑 ...
    
    # 通知需求提出者
    req_author = await get_requirement_author(project_id, req_iid)
    if req_author and str(req_author) != str(current_user.global_user_id):
        await push_notification(
            str(req_author),
            f"📋 您的需求 #{req_iid} 已被 {current_user.full_name} 评审为: {new_state}",
            "info",
            metadata={"req_iid": req_iid, "new_state": new_state}
        )
```

---

### 阶段3: 辅助查询函数

创建统一的干系人查询工具函数：

```python
async def get_project_stakeholders(project_id: int) -> List[str]:
    \"\"\"获取项目干系人的用户ID列表\"\"\"
    # 实际实现中应查询数据库或 GitLab API
    # 简化演示：返回空列表表示未配置
    return []

async def get_requirement_author(project_id: int, req_iid: int) -> Optional[str]:
    \"\"\"获取需求创建者的用户ID\"\"\"
    # 从 GitLab API 或本地数据库查询需求创建者
    return None
```

---

## 🧪 验证测试

### 测试用例1: 质量门禁拦截通知
1. 触发质量门禁检查失败
2. 验证项目负责人收到SSE推送
3. 验证消息内容包含 `project_id` 元数据

### 测试用例2: 测试执行失败通知
1. 执行一个测试用例并标记为失败
2. 验证用例创建者收到SSE推送
3. 验证消息包含 `issue_iid` 元数据

### 测试用例3: 需求评审通知
1. 更新一个需求的评审状态
2. 验证需求创建者收到SSE推送（评审人除外）
3. 验证消息包含 `new_state` 信息

---

## 📊 预期收益

1. **精准推送**: 相关人员第一时间收到通知，提升响应速度
2. **减少噪音**: 避免全员广播造成的信息过载
3. **可追溯性**: 推送日志记录，方便排查问题
4. **用户体验**: 实时收到关注事项的状态变更

---

## 📝 实施检查清单

- [ ] 增强 `push_notification` 函数（支持单播/多播/广播）
- [ ] 质量门禁场景：查询项目负责人并推送
- [ ] 测试执行失败场景：通知用例创建者和需求负责人
- [ ] 需求评审场景：通知需求提出者
- [ ] 创建干系人查询辅助函数
- [ ] 编写验证测试脚本
- [ ] 更新P2实施报告

---

**下一阶段**: 执行代码修改并验证
