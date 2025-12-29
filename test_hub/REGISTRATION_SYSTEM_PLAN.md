# Service Desk 注册审批系统实施计划

## 📋 实施概述

完整的注册审批系统包括：
1. 用户注册功能
2. 管理员审批功能
3. 用户数据持久化
4. 登录验证增强
5. 前端注册页面
6. 管理员审批界面

---

## 🎯 实施范围

### 后端功能（main.py）

#### 1. 数据模型和存储
- [x] 添加用户数据存储变量
- [ ] 添加用户数据加载/保存函数
- [ ] 定义用户数据模型

#### 2. API 端点（新增 4 个）
- [ ] `POST /service-desk/auth/register` - 用户注册
- [ ] `POST /service-desk/admin/approve-user` - 审批用户
- [ ] `GET /service-desk/admin/pending-users` - 获取待审批用户列表
- [ ] `GET /service-desk/admin/all-users` - 获取所有用户列表

#### 3. 现有 API 增强
- [ ] 修改 `request_verification_code` - 添加用户状态检查
- [ ] 修改 `login_with_code` - 添加用户验证

---

### 前端页面

#### 1. 注册页面（新建）
- [ ] `service_desk_register.html` - 用户注册表单

#### 2. 管理员页面（新建）
- [ ] `service_desk_admin.html` - 用户审批界面

#### 3. 现有页面修改
- [ ] `service_desk_login.html` - 添加注册入口
- [ ] `service_desk.html` - 添加注册链接

---

## 🔧 详细实施步骤

### 步骤 1: 后端 - 用户数据管理

**文件**: `main.py`

**添加内容**:

```python
# 1. 全局变量（在现有全局变量后添加）
SERVICE_DESK_USERS: Dict[str, Dict[str, Any]] = {}  # {email: user_info}
SERVICE_DESK_USERS_FILE = Path(__file__).parent / "service_desk_users.json"

# 2. 数据加载函数
def load_service_desk_users():
    """从 JSON 文件加载 Service Desk 用户数据"""
    global SERVICE_DESK_USERS
    if SERVICE_DESK_USERS_FILE.exists():
        try:
            with open(SERVICE_DESK_USERS_FILE, 'r', encoding='utf-8') as f:
                SERVICE_DESK_USERS = json.load(f)
            logger.info(f"Loaded {len(SERVICE_DESK_USERS)} Service Desk users")
        except Exception as e:
            logger.error(f"Failed to load Service Desk users: {e}")
            SERVICE_DESK_USERS = {}
    else:
        SERVICE_DESK_USERS = {}

# 3. 数据保存函数
def save_service_desk_users():
    """将 Service Desk 用户数据保存到 JSON 文件"""
    try:
        with open(SERVICE_DESK_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(SERVICE_DESK_USERS, f, ensure_ascii=False, indent=2)
        logger.debug(f"Saved {len(SERVICE_DESK_USERS)} users")
    except Exception as e:
        logger.error(f"Failed to save Service Desk users: {e}")

# 4. 在 main 函数中添加加载调用
if __name__ == "__main__":
    load_service_desk_tickets()
    load_service_desk_users()  # 新增
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

### 步骤 2: 后端 - 注册 API

**添加位置**: 在登录 API 后

```python
@app.post("/service-desk/auth/register")
async def register_user(
    email: str,
    name: str,
    company: str,
    phone: Optional[str] = None,
    reason: Optional[str] = None
):
    """用户注册（需要管理员审批）
    
    Args:
        email: 邮箱地址
        name: 姓名
        company: 公司/部门
        phone: 联系电话（可选）
        reason: 注册原因（可选）
    
    Returns:
        dict: 注册结果
    
    Raises:
        HTTPException: 邮箱已注册或格式错误时抛出
    """
    # 验证邮箱格式
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="无效的邮箱地址")
    
    # 检查是否已注册
    if email in SERVICE_DESK_USERS:
        user = SERVICE_DESK_USERS[email]
        if user["status"] == "approved":
            raise HTTPException(status_code=400, detail="此邮箱已注册并审批通过，请直接登录")
        elif user["status"] == "pending":
            raise HTTPException(status_code=400, detail="此邮箱正在等待审批，请耐心等待")
        elif user["status"] == "rejected":
            raise HTTPException(status_code=403, detail="此邮箱的注册申请已被拒绝，如有疑问请联系管理员")
    
    # 创建用户记录
    SERVICE_DESK_USERS[email] = {
        "email": email,
        "name": name,
        "company": company,
        "phone": phone,
        "reason": reason,
        "status": "pending",  # pending, approved, rejected
        "created_at": datetime.now().isoformat(),
        "approved_at": None,
        "approved_by": None,
        "reject_reason": None
    }
    
    save_service_desk_users()
    
    logger.info(f"New user registration: {email} ({name}) from {company}")
    
    return {
        "status": "success",
        "message": "注册申请已提交，请等待管理员审批。审批通过后您将收到通知邮件。",
        "email": email,
        "name": name
    }
```

---

### 步骤 3: 后端 - 审批 API

```python
# 管理员令牌（临时方案，生产环境应使用数据库）
ADMIN_TOKEN = "admin_secret_token_2025"  # TODO: 从配置文件读取

@app.post("/service-desk/admin/approve-user")
async def approve_user(
    email: str,
    approved: bool,
    admin_token: str,
    reject_reason: Optional[str] = None
):
    """审批用户注册（管理员功能）
    
    Args:
        email: 用户邮箱
        approved: 是否批准（True=批准，False=拒绝）
        admin_token: 管理员令牌
        reject_reason: 拒绝原因（拒绝时必填）
    
    Returns:
        dict: 审批结果
    
    Raises:
        HTTPException: 权限不足或用户不存在时抛出
    """
    # 验证管理员权限
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员令牌无效")
    
    if email not in SERVICE_DESK_USERS:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user = SERVICE_DESK_USERS[email]
    
    if user["status"] != "pending":
        raise HTTPException(
            status_code=400, 
            detail=f"用户状态不是待审批（当前状态：{user['status']}）"
        )
    
    # 拒绝时必须提供原因
    if not approved and not reject_reason:
        raise HTTPException(status_code=400, detail="拒绝时必须提供拒绝原因")
    
    # 更新状态
    user["status"] = "approved" if approved else "rejected"
    user["approved_at"] = datetime.now().isoformat()
    user["approved_by"] = "admin"  # TODO: 使用实际管理员信息
    
    if not approved:
        user["reject_reason"] = reject_reason
    
    save_service_desk_users()
    
    action = "approved" if approved else "rejected"
    logger.info(f"User {email} {action} by admin")
    
    # TODO: 发送邮件通知用户
    
    return {
        "status": "success",
        "email": email,
        "approved": approved,
        "message": f"用户已{('批准' if approved else '拒绝')}"
    }


@app.get("/service-desk/admin/pending-users")
async def get_pending_users(admin_token: str):
    """获取待审批用户列表（管理员功能）
    
    Args:
        admin_token: 管理员令牌
    
    Returns:
        list: 待审批用户列表
    """
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员令牌无效")
    
    pending = [
        user for user in SERVICE_DESK_USERS.values()
        if user["status"] == "pending"
    ]
    
    # 按创建时间倒序
    pending.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "status": "success",
        "total": len(pending),
        "users": pending
    }


@app.get("/service-desk/admin/all-users")
async def get_all_users(admin_token: str, status: Optional[str] = None):
    """获取所有用户列表（管理员功能）
    
    Args:
        admin_token: 管理员令牌
        status: 筛选状态（可选：pending, approved, rejected）
    
    Returns:
        dict: 用户列表
    """
    if admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="管理员令牌无效")
    
    users = list(SERVICE_DESK_USERS.values())
    
    # 状态筛选
    if status:
        users = [u for u in users if u["status"] == status]
    
    # 按创建时间倒序
    users.sort(key=lambda x: x["created_at"], reverse=True)
    
    # 统计
    stats = {
        "total": len(SERVICE_DESK_USERS),
        "pending": len([u for u in SERVICE_DESK_USERS.values() if u["status"] == "pending"]),
        "approved": len([u for u in SERVICE_DESK_USERS.values() if u["status"] == "approved"]),
        "rejected": len([u for u in SERVICE_DESK_USERS.values() if u["status"] == "rejected"])
    }
    
    return {
        "status": "success",
        "stats": stats,
        "users": users
    }
```

---

### 步骤 4: 后端 - 修改登录验证

```python
@app.post("/service-desk/auth/request-code")
async def request_verification_code(email: str):
    """请求登录验证码（带用户审批验证）"""
    
    # 验证邮箱格式
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="无效的邮箱地址")
    
    # 检查用户是否存在且已审批
    if email not in SERVICE_DESK_USERS:
        raise HTTPException(
            status_code=403,
            detail="此邮箱未注册。请先注册并等待管理员审批。"
        )
    
    user = SERVICE_DESK_USERS[email]
    
    if user["status"] == "pending":
        raise HTTPException(
            status_code=403,
            detail="您的注册申请正在审批中，请耐心等待。如有疑问请联系管理员。"
        )
    elif user["status"] == "rejected":
        reject_reason = user.get("reject_reason", "未提供原因")
        raise HTTPException(
            status_code=403,
            detail=f"您的注册申请已被拒绝。原因：{reject_reason}。如有疑问请联系管理员。"
        )
    elif user["status"] != "approved":
        raise HTTPException(
            status_code=403,
            detail="账号状态异常，请联系管理员"
        )
    
    # 生成验证码（演示模式：固定验证码）
    code = 123456
    
    # 存储验证码（5分钟有效）
    VERIFICATION_CODES[email] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "created_at": datetime.now()
    }
    
    logger.info(f"Generated verification code for approved user {email}: {code}")
    
    # TODO: 在生产环境中，这里应该发送邮件
    # send_verification_email(email, code)
    
    return {
        "status": "success",
        "message": "验证码已生成（演示模式）",
        "demo_code": code,  # 仅演示用，生产环境应删除
        "expires_in": 300  # 5分钟
    }
```

---

## 📊 实施进度

| 步骤 | 内容 | 状态 | 预计时间 |
|------|------|------|---------|
| 1 | 后端 - 用户数据管理 | ⏳ 待实施 | 15分钟 |
| 2 | 后端 - 注册 API | ⏳ 待实施 | 20分钟 |
| 3 | 后端 - 审批 API | ⏳ 待实施 | 30分钟 |
| 4 | 后端 - 登录验证增强 | ⏳ 待实施 | 15分钟 |
| 5 | 前端 - 注册页面 | ⏳ 待实施 | 40分钟 |
| 6 | 前端 - 管理员页面 | ⏳ 待实施 | 50分钟 |
| 7 | 前端 - 现有页面修改 | ⏳ 待实施 | 20分钟 |
| 8 | 测试和文档 | ⏳ 待实施 | 30分钟 |

**总计**: 约 3.5 小时

---

## 🚀 实施顺序

### 阶段 1: 后端实施（约 1.5 小时）
1. ✅ 用户数据管理
2. ✅ 注册 API
3. ✅ 审批 API  
4. ✅ 登录验证增强

### 阶段 2: 前端实施（约 1.5 小时）
5. ✅ 注册页面
6. ✅ 管理员页面
7. ✅ 现有页面修改

### 阶段 3: 测试和文档（约 0.5 小时）
8. ✅ 功能测试
9. ✅ 文档更新

---

## ❓ 确认开始

由于这是一个较大的功能实施，我建议：

**选项 1**: 分阶段实施
- 先完成后端（步骤 1-4）
- 测试后端 API
- 再完成前端（步骤 5-7）

**选项 2**: 一次性完成
- 直接完成所有步骤
- 最后统一测试

**选项 3**: 仅提供完整代码
- 我提供所有代码
- 您自行集成和测试

请告诉我您希望采用哪种方式？

我推荐**选项 1（分阶段实施）**，这样可以确保每个阶段都经过验证。

---

**创建时间**: 2025-12-27  
**预计完成时间**: 约 3.5 小时
