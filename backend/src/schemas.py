from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=160)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class StudentInput(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    school_year: str = ""
    school: str = ""
    guardian_name: str = ""
    guardian_email: str = ""
    guardian_phone: str = ""
    notes: str = ""
    consent_signed_at: datetime | None = None
    archived: bool = False


class AssessmentArea(BaseModel):
    area: str
    score: int = Field(ge=1, le=5)
    observations: str = ""


class AssessmentInput(BaseModel):
    assessed_at: date
    areas: list[AssessmentArea] = Field(min_length=1)


class GoalInput(BaseModel):
    area: str
    description: str
    status: str = "activo"
    target_date: date | None = None


class GoalProgressInput(BaseModel):
    goal_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class SessionInput(BaseModel):
    scheduled_at: datetime
    duration_min: int = Field(default=45, ge=1, le=480)
    status: str = "programada"
    notes: str = ""
    goal_progress: list[GoalProgressInput] = Field(default_factory=list)


class StudentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    first_name: str
    last_name: str
    birth_date: date
    school_year: str
    school: str
    guardian_name: str
    guardian_email: str
    guardian_phone: str
    notes: str
    consent_signed_at: datetime | None
    archived: bool


class AssessmentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    assessed_at: date
    areas: list[AssessmentArea]


class GoalOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    area: str
    description: str
    status: str
    target_date: date | None


class SessionOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    scheduled_at: datetime
    duration_min: int
    status: str
    notes: str
    goal_progress: list[GoalProgressInput]


class AgendaOutput(BaseModel):
    session: SessionOutput
    student_first_name: str
    student_last_name: str


class MaterialInput(BaseModel):
    title: str
    original_text: str


class MaterialOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    title: str
    original_text: str
    adapted_text: str | None
    adaptation_id: str | None
    adapter_url: str | None
    sentences: list[dict]
    attribution: str | None


class ReportInput(BaseModel):
    start_date: date
    end_date: date
    body: str | None = None


class ReportOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    start_date: date
    end_date: date
    body: str
    created_at: datetime
