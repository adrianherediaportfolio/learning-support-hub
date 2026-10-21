from datetime import date, datetime, timedelta

from sqlalchemy import select

from src.database import Base, SessionLocal, engine
from src.models import Assessment, Goal, SessionRecord, Student, User
from src.services.auth import hash_password

Base.metadata.create_all(bind=engine)


def seed() -> None:
    with SessionLocal() as database:
        email = "demo@example.com"
        user = database.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name="Profesional de demostración",
                password_hash=hash_password("Demo-1234"),
            )
            database.add(user)
            database.flush()

        examples = [
            ("Lucía", "Sierra", "lectura"),
            ("Mateo", "Vega", "escritura"),
            ("Inés", "Sol", "atencion"),
        ]
        today = date.today()
        for index, (first_name, last_name, area) in enumerate(examples):
            student = database.scalar(
                select(Student).where(
                    Student.owner_id == user.id,
                    Student.first_name == first_name,
                    Student.last_name == last_name,
                )
            )
            if student is not None:
                continue
            student = Student(
                owner_id=user.id,
                first_name=first_name,
                last_name=last_name,
                birth_date=date(2014 + index, 3 + index, 8 + index),
                school_year="4º de Primaria",
                school="CEIP Los Olivos",
                guardian_name="Familia de ejemplo",
                guardian_email=f"familia{index + 1}@example.test",
                guardian_phone=f"60000000{index + 1}",
                notes="Perfil ficticio para demostración.",
                consent_signed_at=datetime.now(),
            )
            database.add(student)
            database.flush()
            database.add(
                Assessment(
                    student_id=student.id,
                    assessed_at=today - timedelta(days=45),
                    areas=[{"area": area, "score": 3, "observations": "Avance constante."}],
                )
            )
            goal = Goal(
                student_id=student.id,
                area=area,
                description=f"Practicar estrategias de {area} con apoyos visuales.",
                status="activo",
                target_date=today + timedelta(days=60),
            )
            database.add(goal)
            database.flush()
            database.add(
                SessionRecord(
                    student_id=student.id,
                    scheduled_at=datetime.now() + timedelta(days=index + 1),
                    duration_min=45,
                    status="programada",
                    notes="Actividad de práctica ficticia.",
                    goal_progress=[
                        {"goal_id": goal.id, "rating": 3, "comment": "Participación positiva."}
                    ],
                )
            )
        database.commit()


if __name__ == "__main__":
    seed()
