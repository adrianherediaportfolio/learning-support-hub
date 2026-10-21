import asyncio
from datetime import date, datetime, timedelta
from types import SimpleNamespace

import httpx
import jwt
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.database import Base, get_db
from src.main import app, report_context
from src.models import Student
from src.services import reports as report_service


def client_for(path):
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        database = factory()
        try:
            yield database
        finally:
            database.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app), engine


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": "fictitious-pass-123", "full_name": "Ana Demo"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def student_payload() -> dict:
    return {
        "first_name": "Lucía",
        "last_name": "Ejemplo",
        "birth_date": "2015-04-12",
        "school_year": "4º de Primaria",
        "school": "CEIP Los Olivos",
        "guardian_name": "María Ejemplo",
        "guardian_email": "familia@example.com",
        "guardian_phone": "600000001",
        "notes": "Datos ficticios para pruebas.",
        "consent_signed_at": None,
        "archived": False,
    }


def test_registration_login_and_student_ownership(tmp_path) -> None:
    client, engine = client_for(tmp_path / "auth.db")
    try:
        first_token = register(client, "ana@example.com")
        second_token = register(client, "luis@example.com")
        owner_headers = {"Authorization": f"Bearer {first_token}"}
        other_headers = {"Authorization": f"Bearer {second_token}"}

        created = client.post("/api/students", json=student_payload(), headers=owner_headers)
        assert created.status_code == 201
        student_id = created.json()["id"]
        assert client.get(f"/api/students/{student_id}", headers=owner_headers).status_code == 200
        assert client.get(f"/api/students/{student_id}", headers=other_headers).status_code == 404
        assert client.get("/api/students").status_code == 401

        login_response = client.post(
            "/api/auth/login",
            json={"email": "ana@example.com", "password": "fictitious-pass-123"},
        )
        assert login_response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_private_report_context_excludes_identifiers(tmp_path) -> None:
    client, engine = client_for(tmp_path / "privacy.db")
    try:
        token = register(client, "pedagogue@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/students", json=student_payload(), headers=headers)
        student_id = created.json()["id"]
        with next(app.dependency_overrides[get_db]()) as database:
            student = database.get(Student, student_id)
            context = report_context(database, student, date(2025, 1, 1), date(2025, 12, 31))
        assert context == {"first_name": "Lucía", "goals": [], "sessions": []}
        assert "last_name" not in context
        assert "guardian_email" not in context
        assert "school" not in context
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@respx.mock
def test_material_adapter_sends_contract_and_stores_response(tmp_path, monkeypatch) -> None:
    from src.config import settings

    client, engine = client_for(tmp_path / "materials.db")
    monkeypatch.setattr(settings, "adapter_url", "https://adapter.example.test/")
    monkeypatch.setattr(settings, "adapter_api_key", "shared-key")
    route = respx.post("https://adapter.example.test/api/adaptations").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": "adapt-1",
                "adapted_text": "La niña lee.",
                "sentences": [{"text": "La niña lee.", "pictograms": []}],
                "attribution": "Atribución de prueba.",
            },
        )
    )
    try:
        token = register(client, "educator@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        material_id = client.post(
            f"/api/students/{student_id}/materials",
            json={"title": "Lectura de prueba", "original_text": "La niña lee un cuento."},
            headers=headers,
        ).json()["id"]
        response = client.post(
            f"/api/students/{student_id}/materials/{material_id}/adapt",
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["adapted_text"] == "La niña lee."
        assert response.json()["adaptation_id"] == "adapt-1"
        assert response.json()["sentences"][0]["text"] == "La niña lee."
        request = route.calls[0].request
        assert request.headers["X-API-Key"] == "shared-key"
        assert request.read() == (
            b'{"text":"La ni\xc3\xb1a lee un cuento.","level":"lectura_facil",'
            b'"pictograms":true,"source":"learning-support-hub"}'
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_adapter_disabled_returns_503(tmp_path, monkeypatch) -> None:
    from src.config import settings

    client, engine = client_for(tmp_path / "disabled.db")
    monkeypatch.setattr(settings, "adapter_url", "")
    try:
        token = register(client, "staff@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        material_id = client.post(
            f"/api/students/{student_id}/materials",
            json={"title": "Texto", "original_text": "Una frase."},
            headers=headers,
        ).json()["id"]
        response = client.post(
            f"/api/students/{student_id}/materials/{material_id}/adapt",
            headers=headers,
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_all_student_routes_enforce_ownership(tmp_path) -> None:
    client, engine = client_for(tmp_path / "ownership.db")
    try:
        owner_headers = {"Authorization": f"Bearer {register(client, 'owner@example.com')}"}
        other_headers = {"Authorization": f"Bearer {register(client, 'other@example.com')}"}
        student_id = client.post(
            "/api/students", json=student_payload(), headers=owner_headers
        ).json()["id"]
        base = f"/api/students/{student_id}"
        routes = [
            ("GET", base, None),
            ("PATCH", base, student_payload()),
            ("GET", f"{base}/assessments", None),
            (
                "POST",
                f"{base}/assessments",
                {
                    "assessed_at": "2025-01-01",
                    "areas": [
                        {"area": "lectura", "score": 3, "observations": "Prueba."},
                    ],
                },
            ),
            ("GET", f"{base}/goals", None),
            ("POST", f"{base}/goals", {"area": "lectura", "description": "Leer un texto breve."}),
            ("GET", f"{base}/goal-progress", None),
            ("GET", f"{base}/sessions", None),
            ("POST", f"{base}/sessions", {"scheduled_at": "2025-01-01T10:00:00"}),
            ("GET", f"{base}/materials", None),
            ("POST", f"{base}/materials", {"title": "Lectura", "original_text": "Una frase."}),
            ("POST", f"{base}/materials/1/adapt", None),
            ("GET", f"{base}/reports", None),
            ("POST", f"{base}/reports", {"start_date": "2025-01-01", "end_date": "2025-01-31"}),
            ("PUT", f"{base}/reports/1", {"start_date": "2025-01-01", "end_date": "2025-01-31"}),
            ("GET", f"{base}/reports/1/pdf", None),
        ]
        for method, path, payload in routes:
            response = client.request(method, path, json=payload, headers=other_headers)
            assert response.status_code == 404, f"{method} {path}: {response.text}"

        agenda = client.get(
            "/api/sessions?start=2025-01-01T00%3A00%3A00&end=2025-01-31T23%3A59%3A59",
            headers=other_headers,
        )
        assert agenda.status_code == 200
        assert agenda.json() == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_auth_rejects_duplicate_email_wrong_password_expired_invalid_and_missing_token(
    tmp_path,
) -> None:
    client, engine = client_for(tmp_path / "auth-cases.db")
    try:
        token = register(client, "educator@example.com")
        duplicate = client.post(
            "/api/auth/register",
            json={
                "email": "educator@example.com",
                "password": "fictitious-pass-123",
                "full_name": "Ada Prueba",
            },
        )
        assert duplicate.status_code == 409
        wrong_password = client.post(
            "/api/auth/login",
            json={"email": "educator@example.com", "password": "incorrecta"},
        )
        assert wrong_password.status_code == 401
        assert client.get("/api/students").status_code == 401
        assert (
            client.get(
                "/api/students", headers={"Authorization": "Bearer invalid-token"}
            ).status_code
            == 401
        )

        expired = jwt.encode(
            {"sub": "1", "exp": datetime.now() - timedelta(minutes=1)},
            settings.secret_key,
            algorithm=settings.algorithm,
        )
        expired_response = client.get(
            "/api/students", headers={"Authorization": f"Bearer {expired}"}
        )
        assert expired_response.status_code == 401
        assert (
            client.get("/api/students", headers={"Authorization": f"Bearer {token}"}).status_code
            == 200
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_assessment_rating_area_and_report_date_validation(tmp_path) -> None:
    client, engine = client_for(tmp_path / "validation.db")
    try:
        headers = {"Authorization": f"Bearer {register(client, 'validation@example.com')}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        base = f"/api/students/{student_id}"
        for score in (0, 6):
            response = client.post(
                f"{base}/assessments",
                json={
                    "assessed_at": "2025-01-01",
                    "areas": [{"area": "lectura", "score": score}],
                },
                headers=headers,
            )
            assert response.status_code == 422
        invalid_area = client.post(
            f"{base}/assessments",
            json={
                "assessed_at": "2025-01-01",
                "areas": [{"area": "inventada", "score": 3}],
            },
            headers=headers,
        )
        assert invalid_area.status_code == 422
        goal_id = client.post(
            f"{base}/goals",
            json={"area": "lectura", "description": "Leer una frase."},
            headers=headers,
        ).json()["id"]
        for rating in (0, 6):
            response = client.post(
                f"{base}/sessions",
                json={
                    "scheduled_at": "2025-01-01T10:00:00",
                    "goal_progress": [{"goal_id": goal_id, "rating": rating}],
                },
                headers=headers,
            )
            assert response.status_code == 422
        report = client.post(
            f"{base}/reports",
            json={"start_date": "2025-02-01", "end_date": "2025-01-01"},
            headers=headers,
        )
        assert report.status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_agenda_filters_inclusive_date_range_and_archived_students_are_hidden(tmp_path) -> None:
    client, engine = client_for(tmp_path / "agenda.db")
    try:
        headers = {"Authorization": f"Bearer {register(client, 'agenda@example.com')}"}
        active_student = client.post(
            "/api/students", json=student_payload(), headers=headers
        ).json()
        archived_payload = {**student_payload(), "first_name": "Inés", "archived": True}
        archived_student = client.post(
            "/api/students", json=archived_payload, headers=headers
        ).json()
        visible = client.get("/api/students", headers=headers).json()
        assert [item["id"] for item in visible] == [active_student["id"]]
        all_students = client.get("/api/students?include_archived=true", headers=headers).json()
        assert {item["id"] for item in all_students} == {
            active_student["id"],
            archived_student["id"],
        }

        for student_id, scheduled_at in (
            (active_student["id"], "2025-01-10T10:00:00"),
            (active_student["id"], "2025-01-11T10:00:00"),
            (archived_student["id"], "2025-01-10T11:00:00"),
        ):
            response = client.post(
                f"/api/students/{student_id}/sessions",
                json={"scheduled_at": scheduled_at},
                headers=headers,
            )
            assert response.status_code == 201
        agenda = client.get(
            "/api/sessions",
            params={"start": "2025-01-10T10:00:00", "end": "2025-01-10T10:00:00"},
            headers=headers,
        )
        assert len(agenda.json()) == 1
        assert agenda.json()[0]["student_first_name"] == "Lucía"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.mark.parametrize("failure", ["timeout", "server", "malformed-json"])
@respx.mock
def test_adapter_failures_return_502_without_storing_material(
    tmp_path, monkeypatch, failure
) -> None:
    from src.config import settings as app_settings

    client, engine = client_for(tmp_path / f"adapter-{failure}.db")
    monkeypatch.setattr(app_settings, "adapter_url", "https://adapter.example.test")
    route = respx.post("https://adapter.example.test/api/adaptations")
    if failure == "timeout":
        route.mock(side_effect=httpx.ReadTimeout("upstream timed out"))
    elif failure == "server":
        route.mock(return_value=httpx.Response(503, text="unavailable"))
    else:
        route.mock(return_value=httpx.Response(200, text="{not-json"))
    try:
        headers = {"Authorization": f"Bearer {register(client, f'{failure}@example.com')}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        material_id = client.post(
            f"/api/students/{student_id}/materials",
            json={"title": "Texto", "original_text": "Una frase sencilla."},
            headers=headers,
        ).json()["id"]
        response = client.post(
            f"/api/students/{student_id}/materials/{material_id}/adapt",
            headers=headers,
        )
        assert response.status_code == 502
        assert response.json()["detail"] == "Text adaptation service is unavailable"
        stored = client.get(f"/api/students/{student_id}/materials", headers=headers).json()[0]
        assert stored["adapted_text"] is None
        assert stored["adaptation_id"] is None
        assert stored["sentences"] == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_dashboard_summary_is_scoped_to_active_owned_data(tmp_path) -> None:
    client, engine = client_for(tmp_path / "dashboard.db")
    try:
        headers = {"Authorization": f"Bearer {register(client, 'dashboard@example.com')}"}
        student = client.post("/api/students", json=student_payload(), headers=headers).json()
        goal = client.post(
            f"/api/students/{student['id']}/goals",
            json={"area": "lectura", "description": "Leer textos breves."},
            headers=headers,
        )
        assert goal.status_code == 201
        today = datetime.now().replace(microsecond=0)
        session = client.post(
            f"/api/students/{student['id']}/sessions",
            json={"scheduled_at": today.isoformat()},
            headers=headers,
        )
        assert session.status_code == 201
        report = client.post(
            f"/api/students/{student['id']}/reports",
            json={
                "start_date": today.date().isoformat(),
                "end_date": today.date().isoformat(),
                "body": "Resumen de prueba.",
            },
            headers=headers,
        )
        assert report.status_code == 201
        summary = client.get("/api/dashboard", headers=headers)
        assert summary.status_code == 200
        payload = summary.json()
        assert len(payload["today_sessions"]) == 1
        assert len(payload["week_sessions"]) == 1
        assert payload["active_goal_count"] == 1
        assert payload["pending_consent_count"] == 1
        assert payload["latest_reports"][0]["student_first_name"] == "Lucía"
        assert client.get("/api/dashboard").status_code == 401
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_report_fallback_is_editable_and_pdf_downloads(tmp_path, monkeypatch) -> None:
    from src.config import settings

    client, engine = client_for(tmp_path / "reports.db")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "practice_name", "Gabinete de Prueba")
    try:
        token = register(client, "reports@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        client.post(
            f"/api/students/{student_id}/goals",
            json={"area": "lectura", "description": "Practicar lectura compartida."},
            headers=headers,
        )
        created = client.post(
            f"/api/students/{student_id}/reports",
            json={"start_date": "2025-01-01", "end_date": "2025-12-31"},
            headers=headers,
        )
        assert created.status_code == 201
        report = created.json()
        assert "Lucía" in report["body"]
        assert "Practicar lectura compartida" in report["body"]
        assert "Ejemplo" not in report["body"]
        saved = client.put(
            f"/api/students/{student_id}/reports/{report['id']}",
            json={
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "body": "Informe revisado para la familia.",
            },
            headers=headers,
        )
        assert saved.json()["body"] == "Informe revisado para la familia."
        pdf = client.get(
            f"/api/students/{student_id}/reports/{report['id']}/pdf",
            headers=headers,
        )
        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.content.startswith(b"%PDF")
        assert b"Gabinete de Prueba" in pdf.content
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_openai_exception_uses_local_report_template(monkeypatch) -> None:
    from src.config import settings

    class FailingCompletions:
        async def create(self, **kwargs):
            raise RuntimeError("Service unavailable")

    class FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = SimpleNamespace(completions=FailingCompletions())

    monkeypatch.setattr(settings, "openai_api_key", "configured-key")
    monkeypatch.setattr(report_service, "AsyncOpenAI", FakeClient)
    context = {
        "first_name": "Lucía",
        "goals": [{"description": "Leer un párrafo", "status": "activo"}],
        "sessions": [],
    }

    result = asyncio.run(report_service.draft_report(context))

    assert "Hola, familia de Lucía" in result
    assert "Leer un párrafo" in result


def test_report_scrubber_removes_identifiers_and_contact_patterns() -> None:
    student = Student(
        first_name="Lucía",
        last_name="Ejemplo",
        guardian_name="María Ejemplo",
        guardian_email="familia@example.com",
        guardian_phone="600000001",
        school="CEIP Los Olivos",
    )
    comment = (
        "EJEMPLO, mARÍA eJEMPLO, FAMILIA@example.com, 600000001, "
        "ceip los olivos, 699 123 456, contacto@prueba.net"
    )

    scrubbed = report_service.scrub_sensitive_text(comment, student)

    for value in (
        "Ejemplo",
        "María Ejemplo",
        "familia@example.com",
        "600000001",
        "CEIP Los Olivos",
        "699 123 456",
        "contacto@prueba.net",
    ):
        assert value.casefold() not in scrubbed.casefold()
    assert scrubbed.count("[dato omitido]") >= 7


def test_openai_prompt_uses_scrubbed_structured_report_data(tmp_path, monkeypatch) -> None:
    from src.config import settings

    captured = {}

    class CapturingCompletions:
        async def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Informe de prueba."))]
            )

    class FakeClient:
        def __init__(self, api_key: str) -> None:
            self.chat = SimpleNamespace(completions=CapturingCompletions())

    client, engine = client_for(tmp_path / "prompt-privacy.db")
    monkeypatch.setattr(settings, "openai_api_key", "configured-key")
    monkeypatch.setattr(report_service, "AsyncOpenAI", FakeClient)
    try:
        token = register(client, "privacy@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        goal_id = client.post(
            f"/api/students/{student_id}/goals",
            json={"area": "lectura", "description": "Leer un texto breve."},
            headers=headers,
        ).json()["id"]
        client.post(
            f"/api/students/{student_id}/sessions",
            json={
                "scheduled_at": "2025-04-12T10:00:00",
                "status": "realizada",
                "goal_progress": [
                    {
                        "goal_id": goal_id,
                        "rating": 4,
                        "comment": (
                            "EJEMPLO; María Ejemplo; familia@example.com; 600000001; "
                            "CEIP Los Olivos; 699 123 456; contacto@prueba.net"
                        ),
                    }
                ],
            },
            headers=headers,
        )
        response = client.post(
            f"/api/students/{student_id}/reports",
            json={"start_date": "2025-01-01", "end_date": "2025-12-31"},
            headers=headers,
        )

        assert response.status_code == 201
        messages = captured["messages"]
        assert messages[0]["role"] == "system"
        assert "3 a 5 párrafos cortos" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "Objetivos:" in messages[1]["content"]
        assert "Progreso fechado:" in messages[1]["content"]
        prompt = "\n".join(message["content"] for message in messages)
        assert f"Objetivo {goal_id}" in prompt
        for value in (
            "Ejemplo",
            "María Ejemplo",
            "familia@example.com",
            "600000001",
            "CEIP Los Olivos",
            "699 123 456",
            "contacto@prueba.net",
        ):
            assert value.casefold() not in prompt.casefold()
        assert "[dato omitido]" in prompt
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_assessments_goals_session_progress_and_agenda(tmp_path) -> None:
    client, engine = client_for(tmp_path / "case-management.db")
    try:
        token = register(client, "case@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        student_id = client.post("/api/students", json=student_payload(), headers=headers).json()[
            "id"
        ]
        base = f"/api/students/{student_id}"

        assessment = client.post(
            f"{base}/assessments",
            json={
                "assessed_at": "2025-02-01",
                "areas": [{"area": "lectura", "score": 3, "observations": "Lee frases."}],
            },
            headers=headers,
        )
        assert assessment.status_code == 201
        assert assessment.json()["areas"][0]["score"] == 3

        goal = client.post(
            f"{base}/goals",
            json={
                "area": "lectura",
                "description": "Leer un párrafo breve.",
                "target_date": "2025-06-01",
            },
            headers=headers,
        )
        goal_id = goal.json()["id"]
        scheduled_at = datetime.now().replace(microsecond=0)
        session = client.post(
            f"{base}/sessions",
            json={
                "scheduled_at": scheduled_at.isoformat(),
                "duration_min": 45,
                "status": "realizada",
                "notes": "Práctica de lectura.",
                "goal_progress": [{"goal_id": goal_id, "rating": 4, "comment": "Avance positivo."}],
            },
            headers=headers,
        )
        assert session.status_code == 201
        assert session.json()["goal_progress"][0]["rating"] == 4

        progress = client.get(f"{base}/goal-progress", headers=headers)
        assert progress.status_code == 200
        assert progress.json()[0]["goal_id"] == goal_id
        assert progress.json()[0]["rating"] == 4
        agenda = client.get(
            "/api/sessions",
            params={
                "start": (scheduled_at - timedelta(days=1)).isoformat(),
                "end": (scheduled_at + timedelta(days=1)).isoformat(),
            },
            headers=headers,
        )
        assert agenda.status_code == 200
        assert agenda.json()[0]["student_first_name"] == "Lucía"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
