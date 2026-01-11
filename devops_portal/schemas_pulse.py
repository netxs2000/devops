from datetime import date
from typing import Optional

from pydantic import BaseModel


class PulseSubmission(BaseModel):
    """心情指数提交模型。

    Attributes:
        user_email: 用户电子邮箱。
        score: 分数 (1-5)。
        note: 可选的备注信息。
    """
    user_email: str
    score: int
    note: Optional[str] = None


class PulseStatus(BaseModel):
    """心情指数状态响应模型。

    Attributes:
        submitted: 是否已提交。
        message: 返回的消息内容。
    """
    submitted: bool
    message: Optional[str] = None
