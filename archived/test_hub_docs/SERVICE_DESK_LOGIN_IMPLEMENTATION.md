# Service Desk 简单登录功能实现方案

## 📋 功能概述

实现基于邮箱验证码的简单登录系统，让业务方可以：
1. 使用邮箱登录（无需密码）
2. 查看"我的工单"列表
3. 自动填充个人信息

---

## 🎯 实现方案

由于完整实现涉及较多代码修改和邮件服务器配置，我建议采用**分阶段实施**的方式：

### 阶段 1: 模拟登录（无邮件，仅演示）✅ 推荐先实施

**特点**:
- 无需邮件服务器
- 使用固定验证码（123456）
- 快速验证功能
- 适合开发和测试

**实现内容**:
1. 登录 API（生成固定验证码）
2. 验证 API（验证码验证 + 生成令牌）
3. "我的工单" API（需要令牌）
4. 登录页面 UI
5. "我的工单"页面 UI

**优点**:
- ✅ 立即可用
- ✅ 无需外部依赖
- ✅ 验证功能流程

---

### 阶段 2: 真实邮件验证码（生产环境）

**特点**:
- 集成真实邮件服务
- 随机生成验证码
- 发送到用户邮箱

**实现内容**:
1. SMTP 邮件配置
2. 邮件发送功能
3. 验证码生成和过期管理

**需要**:
- SMTP 服务器配置
- 邮箱账号和密码

---

## 🚀 阶段 1 实现（推荐）

### 1. 后端 API

#### API 1: 请求验证码

```python
@app.post("/service-desk/auth/request-code")
async def request_verification_code(email: str):
    """请求登录验证码（模拟版本，使用固定验证码）
    
    Args:
        email: 用户邮箱
    
    Returns:
        dict: 包含提示信息
    """
    # 生成固定验证码（演示用）
    code = 123456
    
    # 存储验证码（5分钟有效）
    VERIFICATION_CODES[email] = {
        "code": code,
        "expires_at": datetime.now() + timedelta(minutes=5),
        "created_at": datetime.now()
    }
    
    logger.info(f"Generated verification code for {email}: {code}")
    
    # 在生产环境中，这里应该发送邮件
    # send_verification_email(email, code)
    
    return {
        "status": "success",
        "message": f"验证码已生成（演示模式）",
        "demo_code": code,  # 仅演示用，生产环境应删除
        "expires_in": 300  # 5分钟
    }
```

#### API 2: 验证码登录

```python
@app.post("/service-desk/auth/login")
async def login_with_code(email: str, code: int):
    """使用验证码登录
    
    Args:
        email: 用户邮箱
        code: 验证码
    
    Returns:
        dict: 包含访问令牌
    """
    # 检查验证码是否存在
    if email not in VERIFICATION_CODES:
        raise HTTPException(status_code=400, detail="请先请求验证码")
    
    stored = VERIFICATION_CODES[email]
    
    # 检查验证码是否正确
    if stored["code"] != code:
        raise HTTPException(status_code=400, detail="验证码错误")
    
    # 检查是否过期
    if datetime.now() > stored["expires_at"]:
        del VERIFICATION_CODES[email]
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    
    # 生成访问令牌（7天有效）
    token = secrets.token_urlsafe(32)
    SESSION_TOKENS[token] = {
        "email": email,
        "expires_at": datetime.now() + timedelta(days=7),
        "created_at": datetime.now()
    }
    
    # 删除已使用的验证码
    del VERIFICATION_CODES[email]
    
    logger.info(f"User {email} logged in successfully")
    
    return {
        "status": "success",
        "token": token,
        "email": email,
        "expires_in": 7 * 24 * 3600  # 7天（秒）
    }
```

#### API 3: 获取我的工单

```python
@app.get("/service-desk/my-tickets")
async def get_my_tickets(token: str):
    """获取当前用户的工单列表
    
    Args:
        token: 访问令牌
    
    Returns:
        List[dict]: 工单列表
    """
    # 验证令牌
    if token not in SESSION_TOKENS:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    
    session = SESSION_TOKENS[token]
    
    # 检查是否过期
    if datetime.now() > session["expires_at"]:
        del SESSION_TOKENS[token]
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    
    email = session["email"]
    
    # 获取该邮箱的所有工单
    my_tickets = [
        ticket for ticket in SERVICE_DESK_TICKETS.values()
        if ticket.get("requester_email") == email
    ]
    
    # 按创建时间倒序
    my_tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "status": "success",
        "email": email,
        "total": len(my_tickets),
        "tickets": my_tickets
    }
```

#### API 4: 登出

```python
@app.post("/service-desk/auth/logout")
async def logout(token: str):
    """登出
    
    Args:
        token: 访问令牌
    
    Returns:
        dict: 登出结果
    """
    if token in SESSION_TOKENS:
        email = SESSION_TOKENS[token]["email"]
        del SESSION_TOKENS[token]
        logger.info(f"User {email} logged out")
        return {"status": "success", "message": "已登出"}
    
    return {"status": "success", "message": "令牌不存在或已失效"}
```

#### API 5: 获取用户信息

```python
@app.get("/service-desk/auth/me")
async def get_current_user(token: str):
    """获取当前登录用户信息
    
    Args:
        token: 访问令牌
    
    Returns:
        dict: 用户信息
    """
    if token not in SESSION_TOKENS:
        raise HTTPException(status_code=401, detail="未登录")
    
    session = SESSION_TOKENS[token]
    
    if datetime.now() > session["expires_at"]:
        del SESSION_TOKENS[token]
        raise HTTPException(status_code=401, detail="登录已过期")
    
    # 统计用户工单
    email = session["email"]
    tickets = [t for t in SERVICE_DESK_TICKETS.values() if t.get("requester_email") == email]
    
    stats = {
        "total": len(tickets),
        "pending": len([t for t in tickets if t.get("status") == "pending"]),
        "in_progress": len([t for t in tickets if t.get("status") == "in-progress"]),
        "completed": len([t for t in tickets if t.get("status") == "completed"]),
        "rejected": len([t for t in tickets if t.get("status") == "rejected"])
    }
    
    return {
        "email": email,
        "logged_in_at": session["created_at"],
        "expires_at": session["expires_at"],
        "ticket_stats": stats
    }
```

---

### 2. 前端页面

#### 页面 1: 登录页面 (`service_desk_login.html`)

**功能**:
- 输入邮箱
- 请求验证码
- 输入验证码
- 登录并保存令牌

#### 页面 2: 我的工单页面 (`service_desk_my_tickets.html`)

**功能**:
- 显示用户信息
- 显示工单列表
- 筛选和排序
- 快速查看工单详情
- 登出按钮

#### 页面 3: 修改现有提交页面

**功能**:
- 检测是否已登录
- 自动填充姓名和邮箱
- 提交后自动跳转到"我的工单"

---

## 📊 数据流程

### 登录流程

```
用户输入邮箱
    ↓
点击"获取验证码"
    ↓
后端生成验证码（演示：123456）
    ↓
用户输入验证码
    ↓
点击"登录"
    ↓
后端验证验证码
    ↓
生成访问令牌
    ↓
前端保存令牌到 localStorage
    ↓
跳转到"我的工单"页面
```

### 访问"我的工单"流程

```
打开"我的工单"页面
    ↓
从 localStorage 读取令牌
    ↓
调用 API 获取工单列表
    ↓
显示工单列表
```

---

## 🔒 安全考虑

### 当前实现（演示版）

1. **固定验证码** - 仅用于演示，不适合生产
2. **令牌存储** - 存储在内存中，重启后失效
3. **无加密** - HTTP 传输（生产环境应使用 HTTPS）

### 生产环境建议

1. **随机验证码** - 6位随机数字
2. **邮件发送** - 通过 SMTP 发送
3. **令牌加密** - 使用 JWT 或加密令牌
4. **HTTPS** - 强制使用 HTTPS
5. **速率限制** - 防止暴力破解
6. **令牌刷新** - 支持令牌续期

---

## 💡 使用示例

### 前端 JavaScript 示例

```javascript
// 1. 请求验证码
async function requestCode() {
    const email = document.getElementById('email').value;
    
    const response = await fetch(`/service-desk/auth/request-code?email=${email}`, {
        method: 'POST'
    });
    
    const result = await response.json();
    alert(`验证码: ${result.demo_code}`);  // 演示模式显示验证码
}

// 2. 登录
async function login() {
    const email = document.getElementById('email').value;
    const code = document.getElementById('code').value;
    
    const response = await fetch(`/service-desk/auth/login?email=${email}&code=${code}`, {
        method: 'POST'
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
        // 保存令牌
        localStorage.setItem('sd_token', result.token);
        localStorage.setItem('sd_email', result.email);
        
        // 跳转到我的工单
        window.location.href = 'service_desk_my_tickets.html';
    }
}

// 3. 获取我的工单
async function loadMyTickets() {
    const token = localStorage.getItem('sd_token');
    
    if (!token) {
        window.location.href = 'service_desk_login.html';
        return;
    }
    
    const response = await fetch(`/service-desk/my-tickets?token=${token}`);
    
    if (response.status === 401) {
        // 登录过期
        localStorage.removeItem('sd_token');
        window.location.href = 'service_desk_login.html';
        return;
    }
    
    const result = await response.json();
    displayTickets(result.tickets);
}

// 4. 登出
function logout() {
    const token = localStorage.getItem('sd_token');
    
    fetch(`/service-desk/auth/logout?token=${token}`, {
        method: 'POST'
    });
    
    localStorage.removeItem('sd_token');
    localStorage.removeItem('sd_email');
    window.location.href = 'service_desk.html';
}
```

---

## ✅ 实施步骤

### 步骤 1: 后端 API（约30分钟）
1. 添加 5 个登录相关 API
2. 测试 API 功能

### 步骤 2: 登录页面（约20分钟）
1. 创建登录页面 UI
2. 实现验证码请求和登录逻辑

### 步骤 3: 我的工单页面（约30分钟）
1. 创建我的工单页面 UI
2. 实现工单列表展示
3. 添加筛选和排序功能

### 步骤 4: 修改现有页面（约15分钟）
1. 修改 Bug/需求提交页面
2. 添加自动填充逻辑
3. 添加登录状态检测

### 步骤 5: 测试（约15分钟）
1. 测试完整登录流程
2. 测试我的工单功能
3. 测试自动填充

**总计**: 约 1.5-2 小时

---

## 🎯 后续升级路径

### 升级到真实邮件验证码

1. 配置 SMTP 服务器
2. 修改验证码生成逻辑（随机6位数）
3. 添加邮件发送功能
4. 移除 `demo_code` 字段

### 升级到 JWT 令牌

1. 安装 `pyjwt` 库
2. 使用 JWT 替代简单令牌
3. 添加令牌刷新机制

---

## ❓ 您的选择

请告诉我您希望：

**A**: 立即实施阶段 1（模拟登录，固定验证码 123456）⭐ 推荐  
**B**: 等待完整实现（需要邮件服务器配置）  
**C**: 仅提供实现代码，您自行集成  

如果选择 A，我将立即为您创建所有必要的代码和页面！

---

**文档版本**: v1.0  
**创建时间**: 2025-12-27
