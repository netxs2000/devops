from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from devops_collector.auth.router import get_db
from devops_portal.schemas_pulse import PulseStatus, PulseSubmission

router = APIRouter(prefix="/devex-pulse", tags=["DevEx Pulse"])


@router.post("/submit", response_model=PulseStatus)
async def submit_pulse_feedback(submission: PulseSubmission,
                                db: Session = Depends(get_db)):
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
        # 检查今日是否已打卡
        result = db.execute(
            text(
                "SELECT 1 FROM satisfaction_records WHERE user_email = :email AND date = :today"
            ), {
                "email": submission.user_email,
                "today": date.today()
            }).fetchone()

        if result:
            return PulseStatus(submitted=True, message="您今日已完成打卡")

        # 插入新记录
        db.execute(
            text("""
                INSERT INTO satisfaction_records (user_email, score, date, created_at, updated_at)
                VALUES (:email, :score, :today, :now, :now)
            """), {
                "email": submission.user_email,
                "score": submission.score,
                "today": date.today(),
                "now": datetime.now()
            })
        db.commit()
        return PulseStatus(submitted=True, message="打卡成功")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_email}", response_model=PulseStatus)
async def check_pulse_status(user_email: str, db: Session = Depends(get_db)):
    """检查用户今日是否已提交反馈。

    Args:
        user_email (str): 用户的电子邮箱地址。
        db (Session): 数据库会话实例。

    Returns:
        PulseStatus: 指示用户是否已提交及相应消息。
    """
    result = db.execute(
        text(
            "SELECT 1 FROM satisfaction_records WHERE user_email = :email AND date = :today"
        ), {
            "email": user_email,
            "today": date.today()
        }).fetchone()

    if result:
        return PulseStatus(submitted=True, message="您今日已完成打卡")
    return PulseStatus(submitted=False, message="待打卡")
