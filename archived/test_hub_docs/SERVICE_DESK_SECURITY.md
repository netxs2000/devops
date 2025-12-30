# Service Desk 登录安全机制说明

## 🔐 当前实现分析

### 当前状态（演示版本）

**重要说明**: 当前实现是**演示版本**，存在以下安全问题：

---

## ⚠️ 当前安全问题

### 1. 没有密码系统

**当前实现**:
- ❌ **没有密码**
- ✅ 仅使用邮箱 + 验证码
- ✅ 验证码固定为 123456（演示模式）

**问题**:
```python
# 当前代码（main.py 第 2283 行）
code = 123456  # 固定验证码，所有人都知道
```

**风险**:
- ⚠️ 任何人知道邮箱就可以登录
- ⚠️ 验证码固定，无安全性
- ⚠️ 无法防止恶意登录

---

### 2. 没有用户注册系统

**当前实现**:
- ❌ **没有用户数据库**
- ❌ **没有注册流程**
- ❌ **没有用户白名单**

**问题**:
```python
# 当前代码
# 任何邮箱都可以请求验证码
VERIFICATION_CODES[email] = {
    "code": code,
    "expires_at": datetime.now() + timedelta(minutes=5)
}
```

**风险**:
- ⚠️ 任何邮箱都可以登录
- ⚠️ 无法控制谁可以使用系统
- ⚠️ 无法防止恶意注册

---

### 3. 数据存储位置

**当前实现**:
```python
# 验证码存储（内存中，服务重启后丢失）
VERIFICATION_CODES: Dict[str, Dict[str, Any]] = {}

# 会话令牌存储（内存中，服务重启后丢失）
SESSION_TOKENS: Dict[str, Dict[str, Any]] = {}
```

**问题**:
- ⚠️ 存储在内存中
- ⚠️ 服务重启后所有会话失效
- ⚠️ 无持久化
- ⚠️ 无法分布式部署

---

## 🛡️ 安全控制方案

### 方案 A: 邮箱白名单（推荐，快速实施）

**实现思路**: 只允许特定邮箱域名或邮箱地址登录

#### 实施步骤

**1. 添加配置文件**

创建 `service_desk_whitelist.json`:
```json
{
  "allowed_domains": [
    "yourcompany.com",
    "partner.com"
  ],
  "allowed_emails": [
    "specific.user@example.com",
    "another.user@gmail.com"
  ],
  "blocked_emails": [
    "spam@example.com"
  ]
}
```

**2. 修改后端代码**

```python
import json
from pathlib import Path

# 加载白名单配置
WHITELIST_FILE = Path(__file__).parent / "service_desk_whitelist.json"

def load_whitelist():
    """加载邮箱白名单配置"""
    if WHITELIST_FILE.exists():
        with open(WHITELIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "allowed_domains": [],
        "allowed_emails": [],
        "blocked_emails": []
    }

WHITELIST = load_whitelist()

def is_email_allowed(email: str) -> bool:
    """检查邮箱是否允许登录
    
    Args:
        email: 用户邮箱
    
    Returns:
        bool: 是否允许
    """
    # 检查黑名单
    if email in WHITELIST.get("blocked_emails", []):
        return False
    
    # 检查白名单邮箱
    if email in WHITELIST.get("allowed_emails", []):
        return True
    
    # 检查白名单域名
    domain = email.split('@')[1] if '@' in email else ''
    if domain in WHITELIST.get("allowed_domains", []):
        return True
    
    return False

# 修改请求验证码 API
@app.post("/service-desk/auth/request-code")
async def request_verification_code(email: str):
    """请求登录验证码（带白名单验证）"""
    
    # 验证邮箱格式
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="无效的邮箱地址")
    
    # 检查白名单
    if not is_email_allowed(email):
        raise HTTPException(
            status_code=403, 
            detail="此邮箱未授权使用 Service Desk，请联系管理员"
        )
    
    # ... 后续代码不变
```

**优点**:
- ✅ 快速实施（~30分钟）
- ✅ 有效控制访问
- ✅ 灵活配置
- ✅ 无需数据库

**缺点**:
- ⚠️ 需要手动维护白名单
- ⚠️ 无法自助注册

---

### 方案 B: 用户注册 + 审批系统

**实现思路**: 用户自助注册，管理员审批后才能使用

#### 数据模型

```python
class ServiceDeskUser(BaseModel):
    """Service Desk 用户模型"""
    email: str
    name: str
    company: str
    phone: Optional[str]
    status: str  # pending, approved, rejected
    created_at: str
    approved_at: Optional[str]
    approved_by: Optional[str]
```

#### 实施步骤

**1. 创建用户数据文件**

```python
# 用户数据存储
SERVICE_DESK_USERS_FILE = Path(__file__).parent / "service_desk_users.json"
SERVICE_DESK_USERS: Dict[str, Dict[str, Any]] = {}

def load_service_desk_users():
    """加载用户数据"""
    global SERVICE_DESK_USERS
    if SERVICE_DESK_USERS_FILE.exists():
        with open(SERVICE_DESK_USERS_FILE, 'r', encoding='utf-8') as f:
            SERVICE_DESK_USERS = json.load(f)

def save_service_desk_users():
    """保存用户数据"""
    with open(SERVICE_DESK_USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(SERVICE_DESK_USERS, f, ensure_ascii=False, indent=2)
```

**2. 添加注册 API**

```python
@app.post("/service-desk/auth/register")
async def register_user(
    email: str,
    name: str,
    company: str,
    phone: Optional[str] = None
):
    """用户注册（需要管理员审批）
    
    Args:
        email: 邮箱
        name: 姓名
        company: 公司
        phone: 电话（可选）
    
    Returns:
        dict: 注册结果
    """
    # 检查是否已注册
    if email in SERVICE_DESK_USERS:
        user = SERVICE_DESK_USERS[email]
        if user["status"] == "approved":
            raise HTTPException(status_code=400, detail="此邮箱已注册并审批通过")
        elif user["status"] == "pending":
            raise HTTPException(status_code=400, detail="此邮箱正在等待审批")
        elif user["status"] == "rejected":
            raise HTTPException(status_code=403, detail="此邮箱的注册申请已被拒绝")
    
    # 创建用户记录
    SERVICE_DESK_USERS[email] = {
        "email": email,
        "name": name,
        "company": company,
        "phone": phone,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "approved_at": None,
        "approved_by": None
    }
    
    save_service_desk_users()
    
    logger.info(f"New user registration: {email} from {company}")
    
    return {
        "status": "success",
        "message": "注册申请已提交，请等待管理员审批",
        "email": email
    }
```

**3. 添加审批 API**

```python
@app.post("/service-desk/admin/approve-user")
async def approve_user(
    email: str,
    admin_token: str,
    approved: bool = True
):
    """审批用户注册（管理员功能）
    
    Args:
        email: 用户邮箱
        admin_token: 管理员令牌
        approved: 是否批准
    
    Returns:
        dict: 审批结果
    """
    # 验证管理员权限
    # TODO: 实现管理员验证逻辑
    
    if email not in SERVICE_DESK_USERS:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user = SERVICE_DESK_USERS[email]
    
    if user["status"] != "pending":
        raise HTTPException(status_code=400, detail="用户状态不是待审批")
    
    # 更新状态
    user["status"] = "approved" if approved else "rejected"
    user["approved_at"] = datetime.now().isoformat()
    user["approved_by"] = "admin"  # TODO: 使用实际管理员信息
    
    save_service_desk_users()
    
    logger.info(f"User {email} {'approved' if approved else 'rejected'}")
    
    return {
        "status": "success",
        "email": email,
        "approved": approved
    }
```

**4. 修改登录验证**

```python
@app.post("/service-desk/auth/request-code")
async def request_verification_code(email: str):
    """请求登录验证码（带用户审批验证）"""
    
    # 检查用户是否存在且已审批
    if email not in SERVICE_DESK_USERS:
        raise HTTPException(
            status_code=403,
            detail="此邮箱未注册，请先注册"
        )
    
    user = SERVICE_DESK_USERS[email]
    
    if user["status"] == "pending":
        raise HTTPException(
            status_code=403,
            detail="您的注册申请正在审批中，请耐心等待"
        )
    elif user["status"] == "rejected":
        raise HTTPException(
            status_code=403,
            detail="您的注册申请已被拒绝，请联系管理员"
        )
    elif user["status"] != "approved":
        raise HTTPException(
            status_code=403,
            detail="账号状态异常，请联系管理员"
        )
    
    # ... 后续代码不变
```

**优点**:
- ✅ 完整的用户管理
- ✅ 管理员可控
- ✅ 用户可自助注册
- ✅ 审批流程

**缺点**:
- ⚠️ 实施复杂（~3-4小时）
- ⚠️ 需要管理员界面
- ⚠️ 需要通知机制

---

### 方案 C: 集成企业 SSO（生产环境推荐）

**实现思路**: 集成企业的单点登录系统（如 LDAP、OAuth2、SAML）

**优点**:
- ✅ 使用企业现有账号
- ✅ 统一认证
- ✅ 安全性高

**缺点**:
- ⚠️ 实施复杂
- ⚠️ 需要企业 SSO 系统

---

## 📊 方案对比

| 方案 | 实施难度 | 安全性 | 灵活性 | 推荐度 |
|------|---------|--------|--------|--------|
| **A: 邮箱白名单** | ⭐ 简单 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐⭐ |
| **B: 注册审批** | ⭐⭐⭐ 复杂 | ⭐⭐⭐⭐ 好 | ⭐⭐⭐⭐⭐ 很好 | ⭐⭐⭐⭐ |
| **C: 企业 SSO** | ⭐⭐⭐⭐⭐ 很复杂 | ⭐⭐⭐⭐⭐ 很好 | ⭐⭐⭐ 中等 | ⭐⭐⭐ |

---

## 🔒 密码存储（如果需要）

### 当前实现

**没有密码系统**:
- 当前使用验证码登录
- 无需密码
- 验证码一次性使用

### 如果需要添加密码

**安全存储方案**:

```python
import hashlib
import secrets

def hash_password(password: str, salt: str = None) -> tuple:
    """安全地哈希密码
    
    Args:
        password: 明文密码
        salt: 盐值（可选）
    
    Returns:
        tuple: (哈希值, 盐值)
    """
    if salt is None:
        salt = secrets.token_hex(32)
    
    # 使用 PBKDF2 哈希
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 迭代次数
    )
    
    return hashed.hex(), salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码
    
    Args:
        password: 明文密码
        hashed: 存储的哈希值
        salt: 盐值
    
    Returns:
        bool: 是否匹配
    """
    new_hash, _ = hash_password(password, salt)
    return new_hash == hashed

# 用户数据模型（带密码）
class ServiceDeskUserWithPassword(BaseModel):
    email: str
    name: str
    password_hash: str  # 存储哈希值
    password_salt: str  # 存储盐值
    status: str
    created_at: str
```

**重要**:
- ✅ **永远不要**存储明文密码
- ✅ 使用强哈希算法（PBKDF2、bcrypt、Argon2）
- ✅ 每个密码使用唯一的盐值
- ✅ 使用足够的迭代次数

---

## 💡 推荐实施方案

### 短期（立即实施）- 方案 A

**邮箱白名单**:
1. 创建 `service_desk_whitelist.json`
2. 配置允许的域名和邮箱
3. 修改验证码请求 API
4. 测试验证

**工作量**: ~30分钟

---

### 中期（按需实施）- 方案 B

**注册审批系统**:
1. 添加用户数据模型
2. 实现注册 API
3. 实现审批 API
4. 创建管理员界面
5. 添加邮件通知

**工作量**: ~3-4小时

---

### 长期（生产环境）- 真实邮件验证码

**替换固定验证码**:
1. 配置 SMTP 服务器
2. 随机生成验证码
3. 发送邮件到用户邮箱
4. 移除演示模式

**工作量**: ~2小时

---

## ✅ 总结

### 当前状态

- ❌ **没有密码系统**（仅验证码）
- ❌ **没有用户数据库**
- ❌ **没有访问控制**
- ⚠️ **任何邮箱都可以登录**（演示模式）

### 数据存储

- **验证码**: 内存中（`VERIFICATION_CODES`）
- **会话令牌**: 内存中（`SESSION_TOKENS`）
- **工单数据**: JSON 文件（`service_desk_tickets.json`）

### 安全建议

**立即实施**:
1. ✅ 添加邮箱白名单（方案 A）
2. ✅ 配置真实邮件验证码
3. ✅ 添加速率限制

**后续优化**:
1. ⏳ 实现注册审批系统（方案 B）
2. ⏳ 令牌持久化（Redis/数据库）
3. ⏳ 集成企业 SSO（方案 C）

---

## ❓ 您的选择

请告诉我您希望：

**A**: 立即实施邮箱白名单（推荐）⭐⭐⭐⭐⭐  
**B**: 实施完整的注册审批系统  
**C**: 仅提供实现方案，您自行决定  

我可以立即为您实施任何方案！🔐

---

**创建时间**: 2025-12-27  
**版本**: v1.0
