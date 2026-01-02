"""TODO: Add module description."""
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from uuid import UUID

class UserRegisterRequest(BaseModel):
    '''"""TODO: Add class description."""'''
    email: EmailStr
    password: str
    full_name: str
    employee_id: Optional[str] = None
    department_code: Optional[str] = None

class UserLoginRequest(BaseModel):
    '''"""TODO: Add class description."""'''
    email: str
    password: str

class Token(BaseModel):
    '''"""TODO: Add class description."""'''
    access_token: str
    token_type: str

class TokenData(BaseModel):
    '''"""TODO: Add class description."""'''
    username: Optional[str] = None

class LocationInfo(BaseModel):
    '''"""TODO: Add class description."""'''
    location_id: str
    location_name: str
    region: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DepartmentInfo(BaseModel):
    '''"""TODO: Add class description."""'''
    org_id: str
    org_name: str
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    '''"""TODO: Add class description."""'''
    global_user_id: UUID
    email: str
    full_name: str
    employee_id: Optional[str]
    is_active: bool
    location: Optional[LocationInfo] = None
    department: Optional[DepartmentInfo] = None
    gitlab_connected: bool = False

    class Config:
        '''"""TODO: Add class description."""'''
        orm_mode = True