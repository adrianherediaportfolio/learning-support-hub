from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies import current_user, owned_student
from src.models import Material, User
from src.schemas import MaterialInput, MaterialOutput
from src.services.adapter_client import (
    AdapterNotConfigured,
    AdapterRequestError,
    request_adaptation,
)

router = APIRouter(prefix="/api", tags=["materials"])


@router.post("/students/{student_id}/materials", status_code=201)
def create_material(
    student_id: int,
    payload: MaterialInput,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> MaterialOutput:
    owned_student(database, student_id, user.id)
    material = Material(student_id=student_id, **payload.model_dump())
    database.add(material)
    database.commit()
    database.refresh(material)
    return material


@router.get("/students/{student_id}/materials")
def list_materials(
    student_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> list[MaterialOutput]:
    owned_student(database, student_id, user.id)
    return list(database.scalars(select(Material).where(Material.student_id == student_id)))


@router.post("/students/{student_id}/materials/{material_id}/adapt")
async def adapt_material(
    student_id: int,
    material_id: int,
    user: User = Depends(current_user),
    database: Session = Depends(get_db),
) -> MaterialOutput:
    owned_student(database, student_id, user.id)
    material = database.scalar(
        select(Material).where(Material.id == material_id, Material.student_id == student_id)
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        base_url, result = await request_adaptation(material.original_text)
    except AdapterNotConfigured:
        raise HTTPException(
            status_code=503, detail="Text adaptation service is not configured"
        ) from None
    except AdapterRequestError as error:
        raise HTTPException(
            status_code=502, detail="Text adaptation service is unavailable"
        ) from error
    material.adapted_text = result["adapted_text"]
    material.adaptation_id = result["id"]
    material.adapter_url = base_url
    material.sentences = result["sentences"]
    material.attributions = result.get("attributions", [])
    material.attribution = result.get("attribution", "")
    database.commit()
    database.refresh(material)
    return material
