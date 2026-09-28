# main.py
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from config import logger
from parser import IndianAddressParser

parser_instance: Optional[IndianAddressParser] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global parser_instance
    logger.info("Starting up...")
    parser_instance = IndianAddressParser()
    logger.info("Parser ready.")
    yield
    logger.info("Shutting down.")

app = FastAPI(title="Indian Address Parser API", version="2.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AddressRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=1000)

    @field_validator("address")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("Address must not be blank.")
        return v.strip()

class ParseResponse(BaseModel):
    original: str
    parsed: dict
    confidence_score: float
    validation_errors: list

@app.get("/")
def root():
    return {"status": "ok", "message": "Indian Address Parser API v2.0", "docs": "/docs"}

@app.get("/health")
def health():
    if parser_instance is None:
        raise HTTPException(status_code=503, detail="Parser not initialized.")
    return {
        "status": "healthy",
        "pincode_count": len(parser_instance.pin_lookup),
        "city_count": len(parser_instance.city_lookup),
    }

@app.post("/parse", response_model=ParseResponse)
def parse_address(request: AddressRequest):
    if parser_instance is None:
        raise HTTPException(status_code=503, detail="Parser not ready.")
    result = parser_instance.parse_address(request.address)
    return ParseResponse(
        original=request.address,
        parsed=result.to_dict(),
        confidence_score=result.confidence_score,
        validation_errors=result.validation_errors,
    )

@app.get("/parse-all")
def parse_all(export: bool = Query(default=True)):
    if parser_instance is None:
        raise HTTPException(status_code=503, detail="Parser not ready.")
    results = parser_instance.parse_all_addresses()
    if export and results:
        parser_instance.export_results_json(results)
    return JSONResponse(content={"message": "Done.", "total": len(results), "results": results})