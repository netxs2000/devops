from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from uuid import UUID

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    employee_id: Optional[str] = None # HR ID, optional for external signups
    department_code: Optional[str] = None

class UserLoginRequest(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LocationInfo(BaseModel):
    location_id: str
    location_name: str
    region: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class DepartmentInfo(BaseModel):
    org_id: str
    org_name: str
    
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    global_user_id: UUID
    email: str
    full_name: str
    employee_id: Optional[str]
    is_active: bool
    location: Optional[LocationInfo] = None
    department: Optional[DepartmentInfo] = None

    class Config:
        orm_mode = True
