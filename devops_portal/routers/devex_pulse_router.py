from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.core.devex_pulse_service import DevexPulseService
from devops_portal.schemas_pulse import PulseStatus, PulseSubmission

router = APIRouter(prefix="/devex-pulse", tags=["DevEx Pulse"])

def get_devex_pulse_service(db: Session = Depends(get_auth_db)) -> DevexPulseService:
    """获取心情指数服务实例。"""
    return DevexPulseService(db)

@router.post("/submit", response_model=PulseStatus)
async def submit_pulse_feedback(submission: PulseSubmission,
                                service: DevexPulseService = Depends(get_devex_pulse_service)):
    """提交每日心情指数反馈。

    Args:
        submission (PulseSubmission): 包含用户邮箱、分数和备注的提交对象。
        db (Session): 数据库会话实例。

    Returns:
        PulseStatus: 提交结果状态和消息。

    Raises:
        HTTPException: 当数据库操作发生异常时抛出 500 错误。
    """
    try:
        return service.submit_feedback(submission)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_email}", response_model=PulseStatus)
async def check_pulse_status(user_email: str, service: DevexPulseService = Depends(get_devex_pulse_service)):
    """检查用户今日是否已提交反馈。

    Args:
        user_email (str): 用户的电子邮箱地址。
        db (Session): 数据库会话实例。

    Returns:
        PulseStatus: 指示用户是否已提交及相应消息。
    """
    return service.get_status(user_email)
