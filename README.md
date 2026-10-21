# Learning Support Hub

[![CI](https://github.com/adrianherediaportfolio/learning-support-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/adrianherediaportfolio/learning-support-hub/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

Learning Support Hub helps a pedagogical practice manage student records, assessments, goals, sessions, adapted materials, and family reports in one private workspace.

## Features

- Professional registration and JWT login.
- Student records with guardian contacts, consent date, notes, and archive status.
- Initial assessments, learning goals, session notes, and goal progress.
- Weekly agenda across the professional's students.
- Editable family report drafts with PDF download.
- Optional text adaptation through Easy Read Adapter.
- Role ownership checks keep each professional's records separate.

## Stack and architecture

- FastAPI, SQLAlchemy, SQLite, PyJWT, and passlib.
- React, TypeScript, Vite, and Tailwind CSS.
- OpenAI report writing with a local Spanish template fallback.
- ReportLab PDF export. No system PDF tools are required by the application.

```text
learning-support-hub/
├── backend/
│   ├── src/main.py           # API routes and ownership checks
│   ├── src/models.py         # SQLAlchemy data model
│   ├── src/services/auth.py  # Password hashing and JWT creation
│   ├── src/seed.py           # Fictitious local sample records
│   └── tests/
├── frontend/src/             # Spanish case management interface
├── docs/api-contract.md      # Shared adapter contract
├── docker-compose.yml
└── .env.example
```

## Local setup

```bash
cp .env.example backend/.env
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m src.seed
uvicorn src.main:app --reload --port 8001
```

The demo login is `demo@example.com` with password `Demo-1234`. All seeded people and contact details are fictitious.

In another terminal:

```bash
cd frontend
cp ../.env.example .env
npm ci
npm run dev
```

Open `http://localhost:5174`. The API documentation is at `http://localhost:8001/docs`.

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:3001`
- API: `http://localhost:8001/docs`

To run Easy Read Adapter from the sibling repository, use its Compose profile:

```bash
ADAPTER_URL=http://adapter:8000 docker compose --profile adapter up --build
```

The profile builds `../easy-read-adapter/backend` and exposes the adapter on `http://localhost:8002`. The Learning Support Hub backend reaches it at `http://adapter:8000`. The adapter response uses contract version 2 pictogram objects and attribution lists.

## Configuration

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Defaults to a local SQLite database. |
| `SECRET_KEY` | JWT signing secret. Replace the example before deployment. |
| `ALGORITHM` | JWT algorithm. Defaults to `HS256`. |
| `ACCESS_TOKEN_MINUTES` | Token lifetime. Defaults to 720 minutes. |
| `OPENAI_API_KEY` | Optional key for family report drafts. Blank uses the local template. |
| `OPENAI_MODEL` | OpenAI model name. Defaults to `gpt-4o-mini`. |
| `ADAPTER_URL` | Optional Easy Read Adapter base URL. Blank disables material adaptation. |
| `ADAPTER_API_KEY` | Optional `X-API-Key` value for the adapter. |
| `ADAPTER_PUBLIC_BASE_URL` | Browser-facing adapter URL for pictogram assets. Defaults to `http://localhost:8002`. |
| `PRACTICE_NAME` | Name printed at the top of exported reports. |
| `CORS_ORIGINS` | Comma-separated list of trusted browser origins. |
| `VITE_API_URL` | API origin compiled into the frontend. |

## API overview

All student routes require a bearer token from `/api/auth/login` or `/api/auth/register`.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register`, `/api/auth/login` | Create an account or sign in. |
| `GET`, `POST` | `/api/students` | List, search, and create student records. |
| `GET`, `PATCH` | `/api/students/{id}` | Read or update an owned student. |
| `GET`, `POST` | `/api/students/{id}/assessments` | Manage assessments. |
| `GET`, `POST` | `/api/students/{id}/goals` | Manage goals. |
| `GET` | `/api/students/{id}/goal-progress` | Read progress points for a chart. |
| `GET`, `POST` | `/api/students/{id}/sessions` | Read or schedule sessions. |
| `GET` | `/api/sessions?start=...&end=...` | Read the user's agenda range. |
| `GET`, `POST` | `/api/students/{id}/materials` | Read or create learning materials. |
| `POST` | `/api/students/{id}/materials/{mid}/adapt` | Request an Easy Read Adapter result. |
| `POST`, `GET` | `/api/students/{id}/reports` | Draft or list family reports. |
| `PUT` | `/api/students/{id}/reports/{rid}` | Save report edits. |
| `GET` | `/api/students/{id}/reports/{rid}/pdf` | Download a report PDF. |
| `GET` | `/api/health` | Check service configuration. |

## Tests

```bash
cd backend
ruff check src tests
ruff format --check src tests
pytest

cd ../frontend
npm ci
npm run lint
npm test
npm run typecheck
npm run build
```

The backend tests use temporary SQLite files and mocked adapter requests.

## Privacy and minors

This application stores personal information about minors. A practice must set its own access, retention, backup, and security procedures and assess its obligations under the RGPD before use with real records. The consent field records a date. It does not replace the practice's consent process or legal review.

Each record is scoped to its professional owner. Use a long, private `SECRET_KEY` and protect SQLite backups. Without `OPENAI_API_KEY`, family report drafts are written locally. When OpenAI is enabled, a report request sends the student's first name, goal areas and descriptions, session dates, and progress ratings or comments. It does not send surname, guardian contact details, school, birth date, or private notes. Review every draft before sharing it.

When Easy Read Adapter is configured, the material's original text is sent to that service. Its default local pictogram chain supports commercial use. ARASAAC is opt-in there, uses CC BY-NC-SA 4.0, and is non-commercial. Stored materials keep the v2 attribution list and can still render old `arasaac_id` records.

## Compatibility

This project integrates with [`easy-read-adapter`](https://github.com/adrianherediaportfolio/easy-read-adapter). The request and response fields are defined in [docs/api-contract.md](docs/api-contract.md). The material adaptation request uses the source label `learning-support-hub`.

## License

This project is proprietary. All rights are reserved. See [LICENSE](LICENSE).
