from typing import Any

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse

from app.services.transform_service import transform_usdm_to_fhir, DEFAULT_MAP_FILE

router = APIRouter()


@router.post("/transform", tags=["Transform"])
def transform(
    usdm: Any = Body(..., description="USDM JSON payload"),
    resource_id: str = Query(default="123", alias="id", description="FHIR resource ID"),
    version: str = Query(default="1", description="FHIR versionId"),
    updated: str = Query(default=None, description="FHIR meta.lastUpdated (ISO 8601)"),
):
    """
    Transformă un USDM JSON (body) în FHIR JSON (răspuns).

    Trimite direct JSON-ul USDM ca request body.
    """
    try:
        fhir_result = transform_usdm_to_fhir(
            usdm_data=usdm,
            map_file=DEFAULT_MAP_FILE,
            resource_id=resource_id,
            version=version,
            updated=updated,
        )
        return JSONResponse(content=fhir_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

