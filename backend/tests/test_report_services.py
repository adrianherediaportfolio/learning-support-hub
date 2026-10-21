from types import SimpleNamespace

from src.services.reports import (
    build_report_messages,
    scrub_sensitive_text,
    template_report,
)


def test_scrubber_handles_case_accents_overlapping_values_and_empty_fields() -> None:
    student = SimpleNamespace(
        last_name="Peña",
        guardian_name="María de la Peña",
        guardian_email="familia@example.com",
        guardian_phone="600 000 001",
        school="Centro del Sol",
    )

    scrubbed = scrub_sensitive_text(
        "PEÑA y PENA. María de la PENA, familia@example.com, 600000001, centro del sol. Sin dato.",
        student,
    )

    assert "peña" not in scrubbed.casefold()
    assert "pena" not in scrubbed.casefold()
    assert "maría" not in scrubbed.casefold()
    assert "familia@example.com" not in scrubbed
    assert "600000001" not in scrubbed
    assert "centro del sol" not in scrubbed.casefold()
    assert scrubbed.count("[dato omitido]") >= 5

    empty_student = SimpleNamespace(
        last_name="",
        guardian_name="",
        guardian_email="",
        guardian_phone="",
        school="",
    )
    assert scrub_sensitive_text("Una nota sin datos.", empty_student) == "Una nota sin datos."


def test_template_report_uses_first_name_and_goal_summary() -> None:
    result = template_report(
        {
            "first_name": "Lucía",
            "goals": [
                {"description": "Leer frases breves", "status": "activo"},
                {"description": "Escribir una idea", "status": "pausado"},
            ],
            "sessions": [{"progress": [{}, {}]}],
        }
    )

    assert "Lucía" in result
    assert "Leer frases breves" in result
    assert "Escribir una idea" not in result
    assert "1 sesiones" in result
    assert "2 observaciones" in result


def test_build_report_messages_is_structured_and_lists_dated_progress() -> None:
    messages = build_report_messages(
        {
            "first_name": "Lucía",
            "goals": [
                {
                    "id": 7,
                    "area": "lectura",
                    "description": "Leer una frase",
                    "status": "activo",
                }
            ],
            "sessions": [
                {
                    "date": "2025-04-12",
                    "progress": [{"goal_id": 7, "rating": 4, "comment": "Lee con más calma."}],
                }
            ],
        }
    )

    assert [message["role"] for message in messages] == ["system", "user"]
    assert "3 a 5 párrafos cortos" in messages[0]["content"]
    assert "No inventes información" in messages[0]["content"]
    assert "Nombre de pila: Lucía" in messages[1]["content"]
    assert "Objetivo 7 | lectura" in messages[1]["content"]
    assert "2025-04-12" in messages[1]["content"]
    assert "valoración 4/5" in messages[1]["content"]
