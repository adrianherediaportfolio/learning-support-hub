import logging
import re
from datetime import date, datetime
from unicodedata import normalize

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.models import Goal, SessionRecord, Student

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)")
ACCENT_GROUPS = {
    "a": "aáàâäãå",
    "e": "eéèêë",
    "i": "iíìîï",
    "o": "oóòôöõ",
    "u": "uúùûü",
    "n": "nñ",
    "c": "cç",
}


def _identifier_pattern(value: str) -> re.Pattern[str]:
    parts = []
    for character in value:
        base = normalize("NFD", character).casefold()[0]
        variants = ACCENT_GROUPS.get(base)
        parts.append(f"[{re.escape(variants)}]" if variants else re.escape(character))
    return re.compile("".join(parts), re.IGNORECASE)


def scrub_sensitive_text(text: str, student: Student) -> str:
    scrubbed = text
    values = sorted(
        {
            value.strip()
            for value in (
                student.last_name,
                student.guardian_name,
                student.guardian_email,
                student.guardian_phone,
                student.school,
            )
            if value and value.strip()
        },
        key=len,
        reverse=True,
    )
    for value in values:
        scrubbed = _identifier_pattern(value).sub("[dato omitido]", scrubbed)
    scrubbed = EMAIL_PATTERN.sub("[dato omitido]", scrubbed)
    return PHONE_PATTERN.sub("[dato omitido]", scrubbed)


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
            {
                "id": goal.id,
                "area": goal.area,
                "description": scrub_sensitive_text(goal.description, student),
                "status": goal.status,
            }
            for goal in goals
        ],
        "sessions": [
            {
                "date": session.scheduled_at.date().isoformat(),
                "progress": [
                    {
                        "goal_id": item["goal_id"],
                        "rating": item["rating"],
                        "comment": scrub_sensitive_text(item.get("comment", ""), student),
                    }
                    for item in session.goal_progress
                ],
            }
            for session in sessions
        ],
    }


def template_report(context: dict) -> str:
    progress_count = sum(len(item["progress"]) for item in context["sessions"])
    active_goals = [goal["description"] for goal in context["goals"] if goal["status"] == "activo"]
    goals_text = ", ".join(active_goals) or "seguir consolidando sus aprendizajes"
    return (
        f"Hola, familia de {context['first_name']}:\n\n"
        f"Durante este periodo hemos acompañado a {context['first_name']} en "
        f"{len(context['sessions'])} sesiones. Hemos trabajado en {goals_text}. "
        f"Se han registrado {progress_count} observaciones de progreso.\n\n"
        "Gracias por acompañar este proceso. Seguiremos trabajando de forma coordinada."
    )


def build_report_messages(context: dict) -> list[dict[str, str]]:
    system = (
        "Redacta un informe para la familia en español cálido y claro. "
        "Escribe de 3 a 5 párrafos cortos. Usa únicamente los datos proporcionados. "
        "No inventes información. No incluyas etiquetas clínicas ni diagnósticos. "
        "Usa solo el nombre de pila de la persona estudiante."
    )
    goal_lines = (
        "\n".join(
            f"- Objetivo {goal['id']} | {goal['area']}: {goal['description']} "
            f"(estado: {goal['status']})"
            for goal in context["goals"]
        )
        or "- No hay objetivos registrados."
    )
    progress_lines = (
        "\n".join(
            f"- {session['date']}: "
            + "; ".join(
                f"objetivo {item['goal_id']}, valoración {item['rating']}/5, "
                f"comentario: {item['comment'] or 'sin comentario'}"
                for item in session["progress"]
            )
            for session in context["sessions"]
        )
        or "- No hay progreso registrado."
    )
    user = (
        f"Nombre de pila: {context['first_name']}\n\n"
        f"Objetivos:\n{goal_lines}\n\n"
        f"Progreso fechado:\n{progress_lines}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


async def draft_report(context: dict) -> str:
    if not settings.openai_api_key.strip():
        return template_report(context)
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.3,
            messages=build_report_messages(context),
        )
        return response.choices[0].message.content or template_report(context)
    except Exception:
        logger.exception("OpenAI report drafting failed; using local template")
        return template_report(context)
