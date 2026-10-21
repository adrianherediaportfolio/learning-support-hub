from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import current_user
from src.models import Goal, Report, SessionRecord, Student, User

router = APIRouter(prefix="/api", tags=["dashboard"])


def _session_rows(database: Session, user_id: int, start: datetime, end: datetime) -> list[dict]:
    rows = database.execute(
        select(SessionRecord, Student.first_name, Student.last_name)
        .join(Student, Student.id == SessionRecord.student_id)
        .where(
            Student.owner_id == user_id,
            Student.archived.is_(False),
            SessionRecord.scheduled_at >= start,
            SessionRecord.scheduled_at <= end,
        )
        .order_by(SessionRecord.scheduled_at)
    )
    return [
        {
            "session": {
                "id": session.id,
                "scheduled_at": session.scheduled_at,
                "duration_min": session.duration_min,
                "status": session.status,
                "notes": session.notes,
                "goal_progress": session.goal_progress,
            },
            "student_first_name": first,
            "student_last_name": last,
        }
        for session, first, last in rows
    ]


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), database: Session = Depends(get_db)) -> dict:
    today = date.today()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_start_at = datetime.combine(week_start, time.min)
    week_end_at = datetime.combine(week_end, time.max)

    active_goals = database.scalar(
        select(func.count(Goal.id))
        .join(Student, Student.id == Goal.student_id)
        .where(
            Student.owner_id == user.id,
            Student.archived.is_(False),
            Goal.status == "activo",
        )
    )
    pending_consent = database.scalar(
        select(func.count(Student.id)).where(
            Student.owner_id == user.id,
            Student.archived.is_(False),
            Student.consent_signed_at.is_(None),
        )
    )
    latest_rows = database.execute(
        select(Report, Student.first_name, Student.last_name)
        .join(Student, Student.id == Report.student_id)
        .where(Student.owner_id == user.id, Student.archived.is_(False))
        .order_by(Report.created_at.desc())
        .limit(5)
    )

    return {
        "today_sessions": _session_rows(database, user.id, today_start, today_end),
        "week_sessions": _session_rows(database, user.id, week_start_at, week_end_at),
        "active_goal_count": active_goals or 0,
        "pending_consent_count": pending_consent or 0,
        "latest_reports": [
            {
                "id": report.id,
                "student_id": report.student_id,
                "student_first_name": first,
                "student_last_name": last,
                "start_date": report.start_date,
                "end_date": report.end_date,
                "created_at": report.created_at,
            }
            for report, first, last in latest_rows
        ],
    }
