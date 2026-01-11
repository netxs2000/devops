from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime
from devops_portal.schemas_pulse import PulseSubmission, PulseStatus
from devops_collector.auth.router import get_db

router = APIRouter(prefix="/devex-pulse", tags=["DevEx Pulse"])

@router.post("/submit", response_model=PulseStatus)
async def submit_pulse_feedback(submission: PulseSubmission, db: Session = Depends(get_db)):
    """Submits a daily DevEx Pulse feedback."""
    try:
        # Check if already submitted today
        result = db.execute(
            text("SELECT 1 FROM satisfaction_records WHERE user_email = :email AND date = :today"),
            {"email": submission.user_email, "today": date.today()}
        ).fetchone()

        if result:
            return PulseStatus(submitted=True, message="Already submitted today.")

        # Insert new record
        db.execute(
            text("""
                INSERT INTO satisfaction_records (user_email, score, date, created_at, updated_at)
                VALUES (:email, :score, :today, :now, :now)
            """),
            {
                "email": submission.user_email,
                "score": submission.score,
                "today": date.today(),
                "now": datetime.now()
            }
        )
        db.commit()
        return PulseStatus(submitted=True, message="Feedback recorded.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{user_email}", response_model=PulseStatus)
async def check_pulse_status(user_email: str, db: Session = Depends(get_db)):
    """Checks if the user has submitted feedback today."""
    result = db.execute(
        text("SELECT 1 FROM satisfaction_records WHERE user_email = :email AND date = :today"),
        {"email": user_email, "today": date.today()}
    ).fetchone()
    
    if result:
        return PulseStatus(submitted=True, message="Already submitted.")
    return PulseStatus(submitted=False, message="Pending submission.")
