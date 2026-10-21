from fastapi import APIRouter

from src.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "adapter_enabled": bool(settings.adapter_url.strip())}
