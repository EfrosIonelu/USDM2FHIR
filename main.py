from fastapi import FastAPI

from app.controllers.index_controller import router as index_router
from app.controllers.transform_controller import router as transform_router

app = FastAPI(
    title="USDM2FHIR API",
    description="Converts USDM clinical study JSON to FHIR resources",
    version="1.0.0"
)

app.include_router(index_router)
app.include_router(transform_router)

