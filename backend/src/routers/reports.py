from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.dependencies import current_user, owned_student
from src.models import Report, User
from src.schemas import ReportInput, ReportOutput
from src.services.pdf import render_report_pdf
from src.services.reports import draft_report, report_context

router = APIRouter(prefix="/api", tags=["reports"])


@router.post("/students/{student_id}/reports", status_code=201)
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


@router.get("/students/{student_id}/reports")
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


@router.put("/students/{student_id}/reports/{report_id}")
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


@router.get("/students/{student_id}/reports/{report_id}/pdf")
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
    return Response(
        content=render_report_pdf(report.body, settings.practice_name),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="informe-{report.id}.pdf"'},
    )
