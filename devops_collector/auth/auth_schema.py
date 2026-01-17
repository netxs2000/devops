"""认证模块相关的数据模型协议 (Schemas)。

采用 Pydantic V2 定义全链路一致的请求与响应格式。
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from uuid import UUID

class AuthRegisterRequest(BaseModel):
    """用户注册请求数据。
    
    Attributes:
        email: 用户注册邮箱。
        password: 登录密码。
        full_name: 用户真实姓名。
        employee_id: 员工工号（可选）。
        department_code: 所属部门编码（可选）。
    """
    email: EmailStr
    password: str
    full_name: str
    employee_id: Optional[str] = None
    department_code: Optional[str] = None

class AuthLoginRequest(BaseModel):
    """用户登录请求数据。
    
    Attributes:
        email: 用户邮箱。
        password: 登录密码。
    """
    email: str
    password: str

class AuthToken(BaseModel):
    """认证令牌响应数据。
    
    Attributes:
        access_token: JWT 访问令牌。
        token_type: 令牌类型 (通常为 bearer)。
    """
    access_token: str
    token_type: str

class AuthTokenData(BaseModel):
    """令牌载荷数据。
    
    Attributes:
        username: 从令牌中提取的用户名（通常是邮箱）。
    """
    username: Optional[str] = None

class AuthLocationInfo(BaseModel):
    """地域信息对齐模型。
    
    Attributes:
        location_id: 地点 ID。
        location_name: 地点名称。
        region: 所属大区（可选）。
    """
    location_id: str
    location_name: str
    region: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AuthDepartmentInfo(BaseModel):
    """部门信息对齐模型。
    
    Attributes:
        org_id: 组织 ID。
        org_name: 组织名称。
    """
    org_id: str
    org_name: str
    model_config = ConfigDict(from_attributes=True)

class AuthUserResponse(BaseModel):
    """用户核心信息响应模型。
    
    Attributes:
        global_user_id: 全局唯一用户 ID。
        email: 用户主邮箱。
        full_name: 用户全名。
        employee_id: 员工号。
        is_active: 是否激活。
        location: 地域信息。
        department: 部门信息。
        gitlab_connected: 是否已绑定 GitLab。
    """
    global_user_id: UUID
    email: str
    full_name: str
    employee_id: Optional[str]
    is_active: bool
    location: Optional[AuthLocationInfo] = None
    department: Optional[AuthDepartmentInfo] = None
    roles: List[dict] = []
    gitlab_connected: bool = False

    model_config = ConfigDict(from_attributes=True)
