from datetime import date, datetime
from io import BytesIO
from textwrap import wrap

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import Base, engine, get_db
from src.models import Assessment, Goal, Material, Report, SessionRecord, Student, User
from src.schemas import (
    AgendaOutput,
    AssessmentInput,
    AssessmentOutput,
    GoalInput,
    GoalOutput,
    LoginInput,
    MaterialInput,
    MaterialOutput,
    ReportInput,
    ReportOutput,
    SessionInput,
    SessionOutput,
    StudentInput,
    StudentOutput,
    UserInput,
)
from src.services.auth import create_token, hash_password, verify_password

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Learning Support Hub", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
bearer = HTTPBearer(auto_error=False)
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


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    database: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token") from None
    user = database.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def owned_student(database: Session, student_id: int, user_id: int) -> Student:
    student = database.scalar(
        select(Student).where(Student.id == student_id, Student.owner_id == user_id)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "adapter_enabled": bool(settings.adapter_url.strip())}


@app.post("/api/auth/register", status_code=201)
def register(payload: UserInput, database: Session = Depends(get_db)) -> dict:
    email = payload.email.lower()
    if database.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=email, full_name=payload.full_name, password_hash=hash_password(payload.password)
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return {"access_token": create_token(user.id), "token_type": "bearer"}


@app.post("/api/auth/login")
def login(payload: LoginInput, database: Session = Depends(get_db)) -> dict:
    user = database.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_token(user.id), "token_type": "bearer"}


@app.get("/api/students")
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


@app.post("/api/students", status_code=201)
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


@app.get("/api/students/{student_id}")
def get_student(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> StudentOutput:
    return owned_student(database, student_id, user.id)


@app.patch("/api/students/{student_id}")
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


@app.post("/api/students/{student_id}/assessments", status_code=201)
def create_assessment(
    student_id: int,
    payload: AssessmentInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> AssessmentOutput:
    owned_student(database, student_id, user.id)
    for item in payload.areas:
        if item.area not in REPORTABLE_AREAS:
            raise HTTPException(status_code=422, detail="Invalid assessment area or score")
    assessment = Assessment(student_id=student_id, **payload.model_dump())
    database.add(assessment)
    database.commit()
    database.refresh(assessment)
    return assessment


@app.get("/api/students/{student_id}/assessments")
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


@app.post("/api/students/{student_id}/goals", status_code=201)
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


@app.get("/api/students/{student_id}/goals")
def list_goals(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[GoalOutput]:
    owned_student(database, student_id, user.id)
    return list(database.scalars(select(Goal).where(Goal.student_id == student_id)))


@app.get("/api/students/{student_id}/goal-progress")
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


@app.get("/api/students/{student_id}/sessions")
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


@app.post("/api/students/{student_id}/sessions", status_code=201)
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


@app.get("/api/sessions")
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


@app.post("/api/students/{student_id}/materials", status_code=201)
def create_material(
    student_id: int,
    payload: MaterialInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> MaterialOutput:
    owned_student(database, student_id, user.id)
    material = Material(student_id=student_id, **payload.model_dump())
    database.add(material)
    database.commit()
    database.refresh(material)
    return material


@app.get("/api/students/{student_id}/materials")
def list_materials(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[MaterialOutput]:
    owned_student(database, student_id, user.id)
    return list(database.scalars(select(Material).where(Material.student_id == student_id)))


@app.post("/api/students/{student_id}/materials/{material_id}/adapt")
async def adapt_material(
    student_id: int,
    material_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> MaterialOutput:
    owned_student(database, student_id, user.id)
    material = database.scalar(
        select(Material).where(Material.id == material_id, Material.student_id == student_id)
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    base_url = settings.adapter_url.rstrip("/")
    if not base_url:
        raise HTTPException(status_code=503, detail="Text adaptation service is not configured")
    headers = {"X-API-Key": settings.adapter_api_key} if settings.adapter_api_key.strip() else {}
    body = {
        "text": material.original_text,
        "level": "lectura_facil",
        "pictograms": True,
        "source": "learning-support-hub",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{base_url}/api/adaptations", json=body, headers=headers)
            response.raise_for_status()
        result = response.json()
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502, detail="Text adaptation service is unavailable"
        ) from error
    material.adapted_text = result["adapted_text"]
    material.adaptation_id = result["id"]
    material.adapter_url = base_url
    material.sentences = result["sentences"]
    material.attribution = result["attribution"]
    database.commit()
    database.refresh(material)
    return material


def report_context(database: Session, student: Student, start: date, end: date) -> dict:
    sessions = list(
        database.scalars(
            select(SessionRecord).where(
                SessionRecord.student_id == student.id,
                SessionRecord.scheduled_at >= datetime.combine(start, datetime.min.time()),
                SessionRecord.scheduled_at <= datetime.combine(end, datetime.max.time()),
                SessionRecord.status == "realizada",
            )
        )
    )
    goals = list(database.scalars(select(Goal).where(Goal.student_id == student.id)))
    return {
        "first_name": student.first_name,
        "goals": [
            {"area": goal.area, "description": goal.description, "status": goal.status}
            for goal in goals
        ],
        "sessions": [
            {
                "date": session.scheduled_at.date().isoformat(),
                "progress": [
                    {"rating": item["rating"], "comment": item.get("comment", "")}
                    for item in session.goal_progress
                ],
            }
            for session in sessions
        ],
    }


async def draft_report(context: dict) -> str:
    if not settings.openai_api_key.strip():
        progress_count = sum(len(item["progress"]) for item in context["sessions"])
        active_goals = [
            goal["description"] for goal in context["goals"] if goal["status"] == "activo"
        ]
        goals_text = ", ".join(active_goals) or "seguir consolidando sus aprendizajes"
        return (
            f"Hola, familia de {context['first_name']}:\n\n"
            f"Durante este periodo hemos acompañado a {context['first_name']} en "
            f"{len(context['sessions'])} sesiones. Hemos trabajado en {goals_text}. "
            f"Se han registrado {progress_count} observaciones de progreso.\n\n"
            "Gracias por acompañar este proceso. Seguiremos trabajando de forma coordinada."
        )
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = "Usa solo estos datos y menciona al estudiante por su nombre: " + str(context)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": "Redacta informes familiares cálidos y claros en español.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return response.choices[0].message.content or ""


@app.post("/api/students/{student_id}/reports", status_code=201)
async def create_report(
    student_id: int,
    payload: ReportInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> ReportOutput:
    student = owned_student(database, student_id, user.id)
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not precede start date")
    context = report_context(database, student, payload.start_date, payload.end_date)
    body = payload.body if payload.body is not None else await draft_report(context)
    report = Report(
        student_id=student_id, start_date=payload.start_date, end_date=payload.end_date, body=body
    )
    database.add(report)
    database.commit()
    database.refresh(report)
    return report


@app.get("/api/students/{student_id}/reports")
def list_reports(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[ReportOutput]:
    owned_student(database, student_id, user.id)
    return list(
        database.scalars(
            select(Report).where(Report.student_id == student_id).order_by(Report.created_at.desc())
        )
    )


@app.put("/api/students/{student_id}/reports/{report_id}")
def update_report(
    student_id: int,
    report_id: int,
    payload: ReportInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> ReportOutput:
    owned_student(database, student_id, user.id)
    report = database.scalar(
        select(Report).where(Report.id == report_id, Report.student_id == student_id)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not precede start date")
    report.start_date = payload.start_date
    report.end_date = payload.end_date
    if payload.body is not None:
        report.body = payload.body
    database.commit()
    database.refresh(report)
    return report


@app.get("/api/students/{student_id}/reports/{report_id}/pdf")
def report_pdf(
    student_id: int,
    report_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> Response:
    owned_student(database, student_id, user.id)
    report = database.scalar(
        select(Report).where(Report.id == report_id, Report.student_id == student_id)
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setTitle(f"Informe de {settings.practice_name}")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(50, height - 55, settings.practice_name)
    pdf.setFont("Helvetica", 10)
    y = height - 90
    for paragraph in report.body.splitlines():
        for line in wrap(paragraph, 95) or [""]:
            if y < 55:
                pdf.showPage()
                y = height - 55
                pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, line.encode("latin-1", "replace").decode("latin-1"))
            y -= 16
    pdf.save()
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-{report.id}.pdf"'},
    )
