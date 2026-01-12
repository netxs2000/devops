"""认证模块相关的数据模型协议 (Schemas)。

采用 Pydantic V2 定义全链路一致的请求与响应格式。
"""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from uuid import UUID

class AuthRegisterRequest(BaseModel):
    """用户注册请求数据。"""
    email: EmailStr
    password: str
    full_name: str
    employee_id: Optional[str] = None
    department_code: Optional[str] = None

class AuthLoginRequest(BaseModel):
    """用户登录请求数据。"""
    email: str
    password: str

class AuthToken(BaseModel):
    """认证令牌响应数据。"""
    access_token: str
    token_type: str

class AuthTokenData(BaseModel):
    """令牌载荷数据。"""
    username: Optional[str] = None

class AuthLocationInfo(BaseModel):
    """地域信息对齐模型。"""
    location_id: str
    location_name: str
    region: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AuthDepartmentInfo(BaseModel):
    """部门信息对齐模型。"""
    org_id: str
    org_name: str
    model_config = ConfigDict(from_attributes=True)

class AuthUserResponse(BaseModel):
    """用户核心信息响应模型。"""
    global_user_id: UUID
    email: str
    full_name: str
    employee_id: Optional[str]
    is_active: bool
    location: Optional[AuthLocationInfo] = None
    department: Optional[AuthDepartmentInfo] = None
    gitlab_connected: bool = False

    model_config = ConfigDict(from_attributes=True)
