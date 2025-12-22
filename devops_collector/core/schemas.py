"""DevOps 数据对象 Schema 定义 (Pydantic)

用于对 Raw Data Staging 层提取出的原始 JSON 进行二次校验和结构化。
提供类型提示、默认值填充以及数据清洗功能。
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

class GitLabUserSchema(BaseModel):
    """GitLab 用户原始数据结构校验
    
    Attributes:
        id: 用户 ID
        username: 用户名
        name: 显示名称
        email: 邮箱地址
        state: 用户状态 (active/blocked)
        skype: Skype ID (alias for skypeid. equals department)
    """
    id: int
    username: str
    name: str
    email: Optional[str] = None
    state: str = "active"
    skype: Optional[str] = Field(None, alias="skypeid") # 演示别名映射

class GitLabMRSchema(BaseModel):
    """GitLab Merge Request 原始数据结构校验
    
    Attributes:
        id: MR 全局 ID
        iid: 项目内 MR 编号
        project_id: 归属项目 ID
        title: MR 标题
        description: MR 描述
        state: MR 状态 (opened, closed, merged, locked)
        author: 作者信息
        created_at: 创建时间
        merged_at: 合并时间
    """
    id: int
    iid: int
    project_id: int
    title: str
    description: Optional[str] = ""
    state: str
    author: GitLabUserSchema
    created_at: datetime
    merged_at: Optional[datetime] = None
    
    @validator('state')
    def validate_state(cls, v):
        allowed = {'opened', 'closed', 'merged', 'locked'}
        if v not in allowed:
            raise ValueError(f"Invalid MR state: {v}")
        return v

class StagingDataBundle(BaseModel):
    """Staging 层数据包通用包装
    
    Attributes:
        source: 数据源名称
        entity_type: 实体类型
        external_id: 外部系统 ID
        payload: 原始 JSON 数据
        collected_at: 采集时间
    """
    source: str
    entity_type: str
    external_id: str
    payload: Dict[str, Any]
    collected_at: datetime = Field(default_factory=datetime.utcnow)

def validate_gitlab_mr(raw_payload: Dict[str, Any]) -> GitLabMRSchema:
    """工具函数：验证并转换 GitLab MR
    
    Args:
        raw_payload: 原始字典数据
        
    Returns:
        GitLabMRSchema: 验证后的 Pydantic 对象
    """
    return GitLabMRSchema(**raw_payload)
