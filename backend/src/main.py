from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from src.config import settings
from src.database import Base, engine
from src.routers import auth, dashboard, health, materials, reports, students
from src.services.reports import report_context

Base.metadata.create_all(bind=engine)
with engine.begin() as connection:
    columns = {column["name"] for column in inspect(connection).get_columns("materials")}
    if "attributions" not in columns:
        connection.execute(text("ALTER TABLE materials ADD COLUMN attributions JSON"))
app = FastAPI(title="Learning Support Hub", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(students.router)
app.include_router(materials.router)
app.include_router(reports.router)

__all__ = ["app", "report_context"]
