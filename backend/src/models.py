from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(160))


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date] = mapped_column(Date)
    school_year: Mapped[str] = mapped_column(String(80), default="")
    school: Mapped[str] = mapped_column(String(160), default="")
    guardian_name: Mapped[str] = mapped_column(String(160), default="")
    guardian_email: Mapped[str] = mapped_column(String(320), default="")
    guardian_phone: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    consent_signed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    assessed_at: Mapped[date] = mapped_column(Date)
    areas: Mapped[list] = mapped_column(JSON, default=list)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    area: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="activo")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    duration_min: Mapped[int] = mapped_column(Integer, default=45)
    status: Mapped[str] = mapped_column(String(20), default="programada")
    notes: Mapped[str] = mapped_column(Text, default="")
    goal_progress: Mapped[list] = mapped_column(JSON, default=list)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    original_text: Mapped[str] = mapped_column(Text)
    adapted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    adaptation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    adapter_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sentences: Mapped[list] = mapped_column(JSON, default=list)
    attributions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    attribution: Mapped[str | None] = mapped_column(Text, nullable=True)
