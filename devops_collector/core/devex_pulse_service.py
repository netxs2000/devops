"""开发人员体验 (DevEx) 心情指数业务服务层。

该模块封装了“心情指数打卡”的核心业务逻辑。
"""
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from devops_portal.schemas_pulse import PulseStatus, PulseSubmission

logger = logging.getLogger(__name__)

class DevexPulseService:
    """DevEx 心情指数业务逻辑服务。"""

    def __init__(self, session: Session):
        """初始化服务。

        Args:
            session (Session): 数据库会话。
        """
        self.session = session

    def get_status(self, user_email: str) -> PulseStatus:
        """检查用户今日打卡状态。"""
        result = self.session.execute(
            text("SELECT 1 FROM satisfaction_records WHERE user_email = :email AND date = :today"),
            {"email": user_email, "today": date.today()}
        ).fetchone()

        if result:
            return PulseStatus(submitted=True, message="您今日已完成打卡")
        return PulseStatus(submitted=False, message="待打卡")

    def submit_feedback(self, submission: PulseSubmission) -> PulseStatus:
        """提交打卡反馈。"""
        # 检查是否已打卡
        if self.get_status(submission.user_email).submitted:
            return PulseStatus(submitted=True, message="您今日已完成打卡")

        # 插入新记录
        self.session.execute(
            text("""
                INSERT INTO satisfaction_records (user_email, score, date, created_at, updated_at)
                VALUES (:email, :score, :today, :now, :now)
            """), {
                "email": submission.user_email,
                "score": submission.score,
                "today": date.today(),
                "now": datetime.now()
            })
        self.session.commit()
        return PulseStatus(submitted=True, message="打卡成功")
