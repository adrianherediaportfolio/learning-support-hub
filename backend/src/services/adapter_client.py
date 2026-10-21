import httpx

from src.config import settings


class AdapterNotConfigured(Exception):
    pass


class AdapterRequestError(Exception):
    pass


async def request_adaptation(original_text: str) -> tuple[str, dict]:
    base_url = settings.adapter_url.rstrip("/")
    if not base_url:
        raise AdapterNotConfigured
    headers = {"X-API-Key": settings.adapter_api_key} if settings.adapter_api_key.strip() else {}
    body = {
        "text": original_text,
        "level": "lectura_facil",
        "pictograms": True,
        "source": "learning-support-hub",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{base_url}/api/adaptations", json=body, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise AdapterRequestError from error
    return base_url, response.json()
