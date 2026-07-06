from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "USDM2FHIR API",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

