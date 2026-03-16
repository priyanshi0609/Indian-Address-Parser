"""
main.py — FastAPI application for the Indian Address Parser.

Endpoints
─────────
GET  /                  — root / welcome
GET  /health            — health check (dataset status, version)
POST /parse             — parse a single address
POST /parse/bulk        — parse up to 500 addresses at once
GET  /parse-all         — parse addresses.csv and save to JSON

Run locally:
    uvicorn main:app --reload --port 8000

Swagger UI available at:  http://localhost:8000/docs
ReDoc available at:       http://localhost:8000/redoc
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import logger
from models import (
    AddressRequest,
    BulkAddressRequest,
    BulkParseResponse,
    HealthResponse,
    ParsedAddressResponse,
    SingleParseResponse,
)
from parser import IndianAddressParser

# ──────────────────────────────────────────────────────────────────────────────
# Application metadata
# ──────────────────────────────────────────────────────────────────────────────

APP_VERSION = "1.0.0"
APP_TITLE   = "Indian Address Parser API"
APP_DESC    = """
Parse raw, unstructured Indian addresses into structured JSON fields.

Supports extraction of:
- **Care-of** (S/O, W/O, C/O, D/O …)
- **House / Flat / Plot number**
- **Building name**
- **Street, Locality, Landmark**
- **Village, Subdistrict, District**
- **City, State, PIN code**

Each response includes a **confidence score** (0–1) and a list of missing fields.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Lifespan (replaces deprecated @app.on_event)
# ──────────────────────────────────────────────────────────────────────────────

_parser: IndianAddressParser | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _parser
    logger.info("🚀  Starting Indian Address Parser API …")
    _parser = IndianAddressParser()
    logger.info("✅  Parser ready.")
    yield
    logger.info("🛑  Shutting down.")


# ──────────────────────────────────────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESC,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Request-timing middleware (useful for profiling)
# ──────────────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Helper: guard against uninitialised parser
# ──────────────────────────────────────────────────────────────────────────────

def _get_parser() -> IndianAddressParser:
    if _parser is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parser not initialised yet — please retry.",
        )
    return _parser


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", tags=["General"])
def root():
    return {
        "message": f"Welcome to the {APP_TITLE}",
        "version": APP_VERSION,
        "docs":    "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health():
    p = _get_parser()
    datasets_ok = bool(p.city_lookup) or bool(p.pin_lookup)
    return HealthResponse(
        status="ok" if datasets_ok else "degraded",
        version=APP_VERSION,
        datasets_ok=datasets_ok,
    )


@app.post(
    "/parse",
    response_model=SingleParseResponse,
    tags=["Parse"],
    summary="Parse a single address",
)
def parse_single(request: AddressRequest):
    """
    Parse one raw Indian address string.

    - Extracts all available fields.
    - Returns a **confidence_score** (0.0–1.0) and **validation_errors**.
    """
    p      = _get_parser()
    parsed = p.parse_address(request.address)
    return SingleParseResponse(
        original=request.address,
        parsed=ParsedAddressResponse(**parsed.to_dict()),
    )


@app.post(
    "/parse/bulk",
    response_model=BulkParseResponse,
    tags=["Parse"],
    summary="Parse multiple addresses at once",
)
def parse_bulk(request: BulkAddressRequest):
    """
    Parse up to **500** addresses in a single request.

    Returns a list of parsed results in the same order as the input.
    """
    p = _get_parser()

    if len(request.addresses) > 500:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 500 addresses per request.",
        )

    results: List[SingleParseResponse] = []
    for addr in request.addresses:
        parsed = p.parse_address(addr)
        results.append(
            SingleParseResponse(
                original=addr,
                parsed=ParsedAddressResponse(**parsed.to_dict()),
            )
        )

    return BulkParseResponse(total=len(results), results=results)


@app.get(
    "/parse-all",
    tags=["Parse"],
    summary="Parse all addresses in addresses.csv",
)
def parse_all():
    """
    Parse every address in **addresses.csv** and save results to `parsed_output.json`.
    """
    p       = _get_parser()
    results = p.parse_all_addresses()
    p.export_results_json(results)
    return JSONResponse(content={
        "message": "All addresses parsed and saved to parsed_output.json",
        "total":   len(results),
    })


# ──────────────────────────────────────────────────────────────────────────────
# Global exception handler
# ──────────────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again."},
    )