# Learning Support Hub

[![CI](https://github.com/adrianherediaportfolio/learning-support-hub/actions/workflows/ci.yml/badge.svg)](https://github.com/adrianherediaportfolio/learning-support-hub/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![Licencia](https://img.shields.io/badge/Licencia-Propietaria-red)](LICENSE)

Learning Support Hub ayuda a un gabinete pedagógico a gestionar fichas, evaluaciones, objetivos, sesiones, materiales adaptados e informes familiares en un espacio privado.

## Funciones

- Registro profesional e inicio de sesión con JWT.
- Fichas con contactos familiares, fecha de consentimiento, notas y archivo.
- Evaluaciones iniciales, objetivos, sesiones y seguimiento del progreso.
- Agenda semanal con las sesiones de cada profesional.
- Borradores de informes familiares editables y descarga en PDF.
- Adaptación opcional de materiales mediante Easy Read Adapter.
- Comprobaciones de propiedad para separar los datos de cada profesional.

## Tecnología y arquitectura

- FastAPI, SQLAlchemy, SQLite, PyJWT y passlib.
- React, TypeScript, Vite y Tailwind CSS.
- Redacción de informes con OpenAI y plantilla local como alternativa.
- Exportación PDF con ReportLab. La aplicación no requiere herramientas PDF del sistema.

```text
learning-support-hub/
├── backend/
│   ├── src/main.py           # Rutas de API y control de propiedad
│   ├── src/models.py         # Modelo de SQLAlchemy
│   ├── src/services/auth.py  # Hash de contraseñas y creación de JWT
│   ├── src/seed.py           # Datos ficticios para desarrollo
│   └── tests/
├── frontend/src/             # Interfaz profesional en español
├── docs/api-contract.md      # Contrato compartido con el adaptador
├── docker-compose.yml
└── .env.example
```

## Instalación local

```bash
cp .env.example backend/.env
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m src.seed
uvicorn src.main:app --reload --port 8001
```

El acceso de demostración es `demo@example.com` con contraseña `Demo-1234`. Todas las personas y los datos de contacto son ficticios.

En otra terminal:

```bash
cd frontend
cp ../.env.example .env
npm ci
npm run dev
```

Abre `http://localhost:5174`. La documentación de la API está en `http://localhost:8001/docs`.

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:3001`
- API: `http://localhost:8001/docs`

Para ejecutar Easy Read Adapter desde el repositorio hermano, usa su perfil de Compose:

```bash
ADAPTER_URL=http://adapter:8000 docker compose --profile adapter up --build
```

El perfil construye `../easy-read-adapter/backend` y publica el adaptador en `http://localhost:8002`. El backend de Learning Support Hub lo alcanza en `http://adapter:8000`.

## Configuración

| Variable | Uso |
| --- | --- |
| `DATABASE_URL` | URL de SQLAlchemy. El valor inicial usa SQLite local. |
| `SECRET_KEY` | Secreto para firmar JWT. Cambia el valor de ejemplo antes del despliegue. |
| `ALGORITHM` | Algoritmo JWT. El valor inicial es `HS256`. |
| `ACCESS_TOKEN_MINUTES` | Duración del token. El valor inicial es 720 minutos. |
| `OPENAI_API_KEY` | Clave opcional para redactar informes. Si está vacía, se usa una plantilla local. |
| `OPENAI_MODEL` | Modelo de OpenAI. El valor inicial es `gpt-4o-mini`. |
| `ADAPTER_URL` | URL base opcional de Easy Read Adapter. Vacía, desactiva la adaptación. |
| `ADAPTER_API_KEY` | Valor opcional de `X-API-Key` para el adaptador. |
| `PRACTICE_NAME` | Nombre que aparece en los informes PDF. |
| `CORS_ORIGINS` | Lista de orígenes web permitidos, separados por comas. |
| `VITE_API_URL` | Origen de la API incluido en la build del frontend. |

## Resumen de la API

Todas las rutas de estudiantes requieren un token bearer de `/api/auth/login` o `/api/auth/register`.

| Método | Ruta | Uso |
| --- | --- | --- |
| `POST` | `/api/auth/register`, `/api/auth/login` | Crear una cuenta o iniciar sesión. |
| `GET`, `POST` | `/api/students` | Listar, buscar y crear fichas. |
| `GET`, `PATCH` | `/api/students/{id}` | Consultar o editar una ficha propia. |
| `GET`, `POST` | `/api/students/{id}/assessments` | Gestionar evaluaciones. |
| `GET`, `POST` | `/api/students/{id}/goals` | Gestionar objetivos. |
| `GET` | `/api/students/{id}/goal-progress` | Consultar puntos para el gráfico. |
| `GET`, `POST` | `/api/students/{id}/sessions` | Consultar o programar sesiones. |
| `GET` | `/api/sessions?start=...&end=...` | Consultar el periodo de agenda. |
| `GET`, `POST` | `/api/students/{id}/materials` | Consultar o crear materiales. |
| `POST` | `/api/students/{id}/materials/{mid}/adapt` | Solicitar adaptación al servicio. |
| `POST`, `GET` | `/api/students/{id}/reports` | Crear o consultar informes. |
| `PUT` | `/api/students/{id}/reports/{rid}` | Guardar cambios en un informe. |
| `GET` | `/api/students/{id}/reports/{rid}/pdf` | Descargar el PDF. |
| `GET` | `/api/health` | Comprobar la configuración del servicio. |

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

Las pruebas del backend usan archivos SQLite temporales y peticiones simuladas al adaptador.

## Privacidad y menores

La aplicación guarda datos personales de menores. Antes de usarla con fichas reales, el gabinete debe definir sus propios controles de acceso, conservación, copias de seguridad y seguridad, y evaluar sus obligaciones conforme al RGPD. El campo de consentimiento registra una fecha. No sustituye el proceso de consentimiento ni la revisión legal del gabinete.

Cada ficha está vinculada a su profesional. Usa un `SECRET_KEY` privado y largo, y protege las copias SQLite. Sin `OPENAI_API_KEY`, los borradores se redactan localmente. Si OpenAI está activado, la solicitud incluye el nombre de pila, las áreas y descripciones de objetivos, las fechas de sesión y las valoraciones o comentarios de progreso. No incluye apellidos, contactos familiares, centro educativo, fecha de nacimiento ni notas privadas. Revisa cada borrador antes de compartirlo.

Si se configura Easy Read Adapter, se envía a ese servicio el texto original del material. Si allí se activan los pictogramas, algunas palabras pueden enviarse a ARASAAC.

## Compatibilidad

Este proyecto se integra con [`easy-read-adapter`](https://github.com/adrianherediaportfolio/easy-read-adapter). Los campos de solicitud y respuesta están definidos en [docs/api-contract.md](docs/api-contract.md). La solicitud de adaptación usa la etiqueta `learning-support-hub` en `source`.

## Licencia

Este proyecto es propietario. Todos los derechos están reservados. Consulta [LICENSE](LICENSE).
