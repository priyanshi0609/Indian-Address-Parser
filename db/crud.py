"""
db/crud.py — All database read/write operations (CRUD).

CRUD = Create, Read, Update, Delete.

Design rules
────────────
1. Every function is async — it awaits DB operations, never blocks.
2. Every function takes a db: AsyncSession as its first argument.
   The session is created per-request in get_db() and passed in.
3. Functions never call commit() — that's done by get_db() after
   the route finishes. This keeps transaction control in one place.
4. Functions return ORM objects or plain dicts — never raw SQL rows.

Why separate crud.py from models_db.py?
────────────────────────────────────────
models_db.py defines the SCHEMA (what the tables look like).
crud.py defines the BEHAVIOUR (what we do with those tables).
Keeping them separate means:
- You can test DB operations without touching table definitions
- Adding a new query = one new function in crud.py, no schema changes
- Routes stay thin — they call crud functions, not raw SQL
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models_db import ParseFeedback, ParseRequest


# ─────────────────────────────────────────────────────────────────────────────
# parse_requests — WRITE
# ─────────────────────────────────────────────────────────────────────────────

async def save_parse_request(
    db: AsyncSession,
    raw_address: str,
    parsed_output: dict,
    confidence_score: float,
    match_method: str,
) -> ParseRequest:
    """
    Save one address parse result to the database.

    Called after every successful parse in the /parse and /parse/bulk
    endpoints. Returns the saved ORM object so the route can include
    the generated `id` in the response.

    What gets stored
    ─────────────────
    raw_address     → exact original string, untouched
    parsed_output   → the full .to_dict() result as JSONB
    confidence_score → duplicated as a native float column for fast queries
    match_method    → how city/state was resolved
    created_at      → set automatically by the DB (func.now())
    """
    row = ParseRequest(
        raw_address=raw_address,
        parsed_output=parsed_output,
        confidence_score=confidence_score,
        match_method=match_method,
    )
    db.add(row)
    await db.flush()   # flush assigns the auto-generated id without committing
    return row


# ─────────────────────────────────────────────────────────────────────────────
# parse_requests — READ
# ─────────────────────────────────────────────────────────────────────────────

async def get_parse_request(
    db: AsyncSession,
    request_id: int,
) -> Optional[ParseRequest]:
    """
    Fetch a single parse request by its ID.
    Returns None if not found (route will return 404).
    """
    result = await db.execute(
        select(ParseRequest).where(ParseRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def get_parse_history(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    match_method: Optional[str] = None,
) -> list[ParseRequest]:
    """
    Fetch parse history with optional filters.

    Parameters
    ──────────
    limit           Max rows to return (default 50, max enforced in route)
    offset          For pagination: skip this many rows
    min_confidence  Only return parses with score >= this value
    max_confidence  Only return parses with score <= this value
    match_method    Filter by how city/state was resolved

    Results are always ordered most-recent-first.

    Example queries this powers:
    - "Show last 50 parses"             → no filters
    - "Show low-confidence parses"      → max_confidence=0.5
    - "Show PIN-matched parses only"    → match_method='pincode'
    - "Page 2 of history"               → offset=50, limit=50
    """
    query = select(ParseRequest).order_by(desc(ParseRequest.created_at))

    if min_confidence is not None:
        query = query.where(ParseRequest.confidence_score >= min_confidence)
    if max_confidence is not None:
        query = query.where(ParseRequest.confidence_score <= max_confidence)
    if match_method:
        query = query.where(ParseRequest.match_method == match_method)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_parse_count(db: AsyncSession) -> int:
    """Total number of addresses parsed so far."""
    result = await db.execute(select(func.count()).select_from(ParseRequest))
    return result.scalar_one()


async def get_stats(db: AsyncSession) -> dict:
    """
    Return aggregate statistics about all parses.

    Used by the GET /stats endpoint.

    Returns
    ───────
    {
        total_parses:         int,
        avg_confidence:       float,
        high_confidence:      int,   # score >= 0.8
        medium_confidence:    int,   # 0.5 <= score < 0.8
        low_confidence:       int,   # score < 0.5
        by_match_method: {
            pincode: int,
            exact:   int,
            fuzzy:   int,
            none:    int,
        }
    }

    Why aggregate in SQL not Python?
    ─────────────────────────────────
    Fetching all rows to count them in Python = O(n) memory.
    SQL COUNT/AVG runs on the DB server and returns a single number.
    For 1M+ rows, the difference is enormous.
    """
    # Total and average
    totals = await db.execute(
        select(
            func.count(ParseRequest.id).label("total"),
            func.avg(ParseRequest.confidence_score).label("avg_conf"),
            func.sum(
                func.cast(ParseRequest.confidence_score >= 0.8, func.Integer)
            ).label("high"),
        )
    )
    row = totals.one()

    # Confidence buckets via CASE
    from sqlalchemy import case, cast, Integer

    buckets = await db.execute(
        select(
            func.sum(
                cast(ParseRequest.confidence_score >= 0.8, Integer)
            ).label("high"),
            func.sum(
                cast(
                    (ParseRequest.confidence_score >= 0.5) &
                    (ParseRequest.confidence_score < 0.8),
                    Integer
                )
            ).label("medium"),
            func.sum(
                cast(ParseRequest.confidence_score < 0.5, Integer)
            ).label("low"),
        )
    )
    bucket_row = buckets.one()

    # By match method
    method_rows = await db.execute(
        select(
            ParseRequest.match_method,
            func.count(ParseRequest.id).label("cnt"),
        ).group_by(ParseRequest.match_method)
    )

    by_method = {r.match_method: r.cnt for r in method_rows}

    total = row.total or 0
    return {
        "total_parses":      total,
        "avg_confidence":    round(float(row.avg_conf or 0), 3),
        "high_confidence":   int(bucket_row.high or 0),
        "medium_confidence": int(bucket_row.medium or 0),
        "low_confidence":    int(bucket_row.low or 0),
        "by_match_method":   by_method,
    }


# ─────────────────────────────────────────────────────────────────────────────
# parse_feedback — WRITE
# ─────────────────────────────────────────────────────────────────────────────

async def save_feedback(
    db: AsyncSession,
    request_id: int,
    field_name: str,
    correct_value: str,
    notes: Optional[str] = None,
) -> ParseFeedback:
    """
    Save a user correction on a specific parsed field.

    The caller (route) is responsible for verifying that the
    request_id exists before calling this — otherwise the FK
    constraint will raise an IntegrityError.
    """
    row = ParseFeedback(
        request_id=request_id,
        field_name=field_name,
        correct_value=correct_value,
        notes=notes,
    )
    db.add(row)
    await db.flush()
    return row


# ─────────────────────────────────────────────────────────────────────────────
# parse_feedback — READ
# ─────────────────────────────────────────────────────────────────────────────

async def get_feedback_for_request(
    db: AsyncSession,
    request_id: int,
) -> list[ParseFeedback]:
    """All feedback entries for a specific parse request."""
    result = await db.execute(
        select(ParseFeedback)
        .where(ParseFeedback.request_id == request_id)
        .order_by(ParseFeedback.created_at)
    )
    return list(result.scalars().all())


async def get_feedback_summary(db: AsyncSession) -> list[dict]:
    """
    Count how many times each field has been corrected.

    Returns a list sorted by most-corrected field first.
    This is the key accuracy measurement query — it shows you
    which fields your parser gets wrong most often.

    Example output:
        [
            {"field_name": "city",     "correction_count": 45},
            {"field_name": "locality", "correction_count": 23},
            {"field_name": "state",    "correction_count": 8},
        ]
    """
    result = await db.execute(
        select(
            ParseFeedback.field_name,
            func.count(ParseFeedback.id).label("correction_count"),
        )
        .group_by(ParseFeedback.field_name)
        .order_by(desc("correction_count"))
    )
    return [
        {"field_name": r.field_name, "correction_count": r.correction_count}
        for r in result
    ]