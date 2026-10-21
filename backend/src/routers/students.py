from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import current_user, owned_student
from src.models import Assessment, Goal, SessionRecord, Student, User
from src.schemas import (
    AgendaOutput,
    AssessmentInput,
    AssessmentOutput,
    GoalInput,
    GoalOutput,
    SessionInput,
    SessionOutput,
    StudentInput,
    StudentOutput,
)

router = APIRouter(prefix="/api", tags=["students"])
REPORTABLE_AREAS = {
    "lectura",
    "escritura",
    "calculo",
    "atencion",
    "memoria",
    "lenguaje_oral",
    "socioemocional",
    "otra",
}


@router.get("/students")
def list_students(
    search: str = "",
    include_archived: bool = False,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[StudentOutput]:
    query = select(Student).where(Student.owner_id == user.id)
    if not include_archived:
        query = query.where(Student.archived.is_(False))
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where((Student.first_name.ilike(term)) | (Student.last_name.ilike(term)))
    return list(database.scalars(query.order_by(Student.last_name, Student.first_name)))


@router.post("/students", status_code=201)
def create_student(
    payload: StudentInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> StudentOutput:
    student = Student(owner_id=user.id, **payload.model_dump())
    database.add(student)
    database.commit()
    database.refresh(student)
    return student


@router.get("/students/{student_id}")
def get_student(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> StudentOutput:
    return owned_student(database, student_id, user.id)


@router.patch("/students/{student_id}")
def update_student(
    student_id: int,
    payload: StudentInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> StudentOutput:
    student = owned_student(database, student_id, user.id)
    for key, value in payload.model_dump().items():
        setattr(student, key, value)
    database.commit()
    database.refresh(student)
    return student


@router.post("/students/{student_id}/assessments", status_code=201)
def create_assessment(
    student_id: int,
    payload: AssessmentInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> AssessmentOutput:
    owned_student(database, student_id, user.id)
    if any(item.area not in REPORTABLE_AREAS for item in payload.areas):
        raise HTTPException(status_code=422, detail="Invalid assessment area or score")
    assessment = Assessment(student_id=student_id, **payload.model_dump())
    database.add(assessment)
    database.commit()
    database.refresh(assessment)
    return assessment


@router.get("/students/{student_id}/assessments")
def list_assessments(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[AssessmentOutput]:
    owned_student(database, student_id, user.id)
    return list(
        database.scalars(
            select(Assessment)
            .where(Assessment.student_id == student_id)
            .order_by(Assessment.assessed_at)
        )
    )


@router.post("/students/{student_id}/goals", status_code=201)
def create_goal(
    student_id: int,
    payload: GoalInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> GoalOutput:
    owned_student(database, student_id, user.id)
    if payload.area not in REPORTABLE_AREAS or payload.status not in {
        "activo",
        "conseguido",
        "pausado",
    }:
        raise HTTPException(status_code=422, detail="Invalid goal area or status")
    goal = Goal(student_id=student_id, **payload.model_dump())
    database.add(goal)
    database.commit()
    database.refresh(goal)
    return goal


@router.get("/students/{student_id}/goals")
def list_goals(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[GoalOutput]:
    owned_student(database, student_id, user.id)
    return list(database.scalars(select(Goal).where(Goal.student_id == student_id)))


@router.get("/students/{student_id}/goal-progress")
def goal_progress(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[dict]:
    owned_student(database, student_id, user.id)
    sessions = database.scalars(
        select(SessionRecord)
        .where(SessionRecord.student_id == student_id)
        .order_by(SessionRecord.scheduled_at)
    )
    return [
        {"date": session.scheduled_at, **item}
        for session in sessions
        for item in session.goal_progress
    ]


@router.get("/students/{student_id}/sessions")
def list_student_sessions(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[SessionOutput]:
    owned_student(database, student_id, user.id)
    return list(
        database.scalars(
            select(SessionRecord)
            .where(SessionRecord.student_id == student_id)
            .order_by(SessionRecord.scheduled_at.desc())
        )
    )


@router.post("/students/{student_id}/sessions", status_code=201)
def create_session(
    student_id: int,
    payload: SessionInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> SessionOutput:
    owned_student(database, student_id, user.id)
    for item in payload.goal_progress:
        goal = database.get(Goal, item.goal_id)
        if goal is None or goal.student_id != student_id:
            raise HTTPException(status_code=422, detail="Invalid goal progress")
    if payload.status not in {"programada", "realizada", "cancelada"}:
        raise HTTPException(status_code=422, detail="Invalid session status")
    record = SessionRecord(student_id=student_id, **payload.model_dump())
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


@router.get("/sessions")
def agenda(
    start: datetime,
    end: datetime,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[AgendaOutput]:
    rows = database.execute(
        select(SessionRecord, Student.first_name, Student.last_name)
        .join(Student, Student.id == SessionRecord.student_id)
        .where(
            Student.owner_id == user.id,
            SessionRecord.scheduled_at >= start,
            SessionRecord.scheduled_at <= end,
        )
        .order_by(SessionRecord.scheduled_at)
    )
    return [
        {"session": session, "student_first_name": first, "student_last_name": last}
        for session, first, last in rows
    ]
