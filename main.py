"""
main.py — FastAPI application for the Indian Address Parser.

Endpoints
─────────
GET  /                    — root / welcome
GET  /health              — health check
POST /parse               — parse single address + save to DB
POST /parse/bulk          — parse up to 500 addresses + save all to DB
GET  /history             — list past parses (paginated, filterable)
GET  /history/{id}        — single parse by ID
POST /feedback            — submit a field correction
GET  /stats               — aggregate stats + feedback summary
GET  /parse-all           — parse addresses.csv (dev utility)
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from config import logger
from db import crud
from db.database import close_db, get_db, init_db
from models import (
    AddressRequest,
    BulkAddressRequest,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    HistoryItem,
    HistoryResponse,
    ParsedAddressResponse,
    SingleParseResponseWithID,
    BulkParseResponseWithIDs,
    StatsResponse,
)
from parser import IndianAddressParser

APP_VERSION = "2.0.0"
APP_TITLE   = "Indian Address Parser API"

_parser: IndianAddressParser | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _parser
    logger.info("Starting Indian Address Parser API v%s", APP_VERSION)
    _parser = IndianAddressParser()
    await init_db()
    logger.info("Parser + Database ready.")
    yield
    await close_db()
    logger.info("Shutdown complete.")


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    elapsed  = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


def _get_parser() -> IndianAddressParser:
    if _parser is None:
        raise HTTPException(status_code=503, detail="Parser not ready.")
    return _parser


@app.get("/", tags=["General"])
def root():
    return {"message": f"Welcome to the {APP_TITLE}", "version": APP_VERSION, "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["General"])
def health():
    p = _get_parser()
    datasets_ok = bool(p.city_lookup) or bool(p.pin_lookup)
    return HealthResponse(status="ok" if datasets_ok else "degraded", version=APP_VERSION, datasets_ok=datasets_ok)


@app.post("/parse", response_model=SingleParseResponseWithID, tags=["Parse"], summary="Parse a single address and save to DB")
async def parse_single(request: AddressRequest, db: AsyncSession = Depends(get_db)):
    """Parse one address, save to database, return result with request_id."""
    p      = _get_parser()
    parsed = p.parse_address(request.address)
    row    = await crud.save_parse_request(
        db,
        raw_address=request.address,
        parsed_output=parsed.to_dict(),
        confidence_score=parsed.confidence_score,
        match_method=parsed.match_method,
    )
    return SingleParseResponseWithID(
        request_id=row.id,
        original=request.address,
        parsed=ParsedAddressResponse(**parsed.to_dict()),
    )


@app.post("/parse/bulk", response_model=BulkParseResponseWithIDs, tags=["Parse"], summary="Parse up to 500 addresses")
async def parse_bulk(request: BulkAddressRequest, db: AsyncSession = Depends(get_db)):
    """Parse multiple addresses. All saved to DB. Each result has a request_id for feedback."""
    p = _get_parser()
    if len(request.addresses) > 500:
        raise HTTPException(status_code=422, detail="Maximum 500 addresses per request.")

    results: List[SingleParseResponseWithID] = []
    for addr in request.addresses:
        parsed = p.parse_address(addr)
        row    = await crud.save_parse_request(
            db,
            raw_address=addr,
            parsed_output=parsed.to_dict(),
            confidence_score=parsed.confidence_score,
            match_method=parsed.match_method,
        )
        results.append(SingleParseResponseWithID(
            request_id=row.id,
            original=addr,
            parsed=ParsedAddressResponse(**parsed.to_dict()),
        ))
    return BulkParseResponseWithIDs(total=len(results), results=results)


@app.get("/history", response_model=HistoryResponse, tags=["History"], summary="List past parse requests")
async def get_history(
    limit:          int             = Query(50,   ge=1, le=200),
    offset:         int             = Query(0,    ge=0),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    match_method:   Optional[str]   = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Paginated history of all parses. Filter by confidence score or match method.
    - Page 2 example: `?offset=50&limit=50`
    - Low-confidence review queue: `?max_confidence=0.5`
    """
    rows  = await crud.get_parse_history(db, limit=limit, offset=offset,
                                          min_confidence=min_confidence,
                                          max_confidence=max_confidence,
                                          match_method=match_method)
    total = await crud.get_parse_count(db)
    return HistoryResponse(
        total=total, limit=limit, offset=offset,
        results=[
            HistoryItem(
                id=r.id, raw_address=r.raw_address,
                parsed_output=r.parsed_output,
                confidence_score=r.confidence_score,
                match_method=r.match_method,
                created_at=r.created_at.isoformat(),
            ) for r in rows
        ],
    )


@app.get("/history/{request_id}", tags=["History"], summary="Get one parse request with its feedback")
async def get_single_history(request_id: int, db: AsyncSession = Depends(get_db)):
    row = await crud.get_parse_request(db, request_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Parse request #{request_id} not found.")
    feedback = await crud.get_feedback_for_request(db, request_id)
    return {
        "id": row.id, "raw_address": row.raw_address,
        "parsed_output": row.parsed_output,
        "confidence_score": row.confidence_score,
        "match_method": row.match_method,
        "created_at": row.created_at.isoformat(),
        "feedback": [
            {"id": f.id, "field_name": f.field_name, "correct_value": f.correct_value,
             "notes": f.notes, "created_at": f.created_at.isoformat()}
            for f in feedback
        ],
    }


@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"], summary="Submit a field correction")
async def submit_feedback(request: FeedbackRequest, db: AsyncSession = Depends(get_db)):
    """
    Report that a specific field was wrong.
    Use the request_id from the /parse response.
    Example: city was 'Kanpur' but should be 'Lucknow'.
    """
    existing = await crud.get_parse_request(db, request.request_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Parse request #{request.request_id} not found.")
    row = await crud.save_feedback(
        db, request_id=request.request_id,
        field_name=request.field_name,
        correct_value=request.correct_value,
        notes=request.notes,
    )
    return FeedbackResponse(
        id=row.id, request_id=row.request_id,
        field_name=row.field_name, correct_value=row.correct_value,
        notes=row.notes, created_at=row.created_at.isoformat(),
    )


@app.get("/stats", response_model=StatsResponse, tags=["Analytics"], summary="Aggregate stats and accuracy metrics")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Total parses, confidence breakdown, match method distribution, most-corrected fields."""
    stats    = await crud.get_stats(db)
    feedback = await crud.get_feedback_summary(db)
    return StatsResponse(
        total_parses=stats["total_parses"],
        avg_confidence=stats["avg_confidence"],
        high_confidence=stats["high_confidence"],
        medium_confidence=stats["medium_confidence"],
        low_confidence=stats["low_confidence"],
        by_match_method=stats["by_match_method"],
        feedback_summary=feedback,
    )


@app.get("/parse-all", tags=["Dev"], summary="Parse all rows in addresses.csv and save to DB")
async def parse_all(db: AsyncSession = Depends(get_db)):
    p       = _get_parser()
    results = p.parse_all_addresses()
    for item in results:
        parsed = item["parsed"]
        await crud.save_parse_request(
            db, raw_address=item["original"], parsed_output=parsed,
            confidence_score=parsed.get("confidence_score", 0.0),
            match_method=parsed.get("match_method", "none"),
        )
    return {"message": f"Parsed and saved {len(results)} addresses to DB."}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred."})