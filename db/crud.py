"""
db/crud.py — All database read/write operations.
"""

from __future__ import annotations
from typing import Optional
from sqlalchemy import Integer, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models_db import ParseFeedback, ParseRequest


async def save_parse_request(
    db: AsyncSession,
    raw_address: str,
    parsed_output: dict,
    confidence_score: float,
    match_method: str,
    user_id: Optional[str] = None,
) -> ParseRequest:
    row = ParseRequest(
        user_id=user_id,
        raw_address=raw_address,
        parsed_output=parsed_output,
        confidence_score=confidence_score,
        match_method=match_method,
    )
    db.add(row)
    await db.flush()
    return row


async def get_parse_request(db: AsyncSession, request_id: int) -> Optional[ParseRequest]:
    result = await db.execute(select(ParseRequest).where(ParseRequest.id == request_id))
    return result.scalar_one_or_none()


async def get_parse_history(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    user_id: Optional[str] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    match_method: Optional[str] = None,
) -> list[ParseRequest]:
    query = select(ParseRequest).order_by(desc(ParseRequest.created_at))

    # Filter by user — each user only sees their own history
    if user_id:
        query = query.where(ParseRequest.user_id == user_id)
    if min_confidence is not None:
        query = query.where(ParseRequest.confidence_score >= min_confidence)
    if max_confidence is not None:
        query = query.where(ParseRequest.confidence_score <= max_confidence)
    if match_method:
        query = query.where(ParseRequest.match_method == match_method)

    result = await db.execute(query.limit(limit).offset(offset))
    return list(result.scalars().all())


async def get_parse_count(db: AsyncSession, user_id: Optional[str] = None) -> int:
    query = select(func.count()).select_from(ParseRequest)
    if user_id:
        query = query.where(ParseRequest.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one()


async def get_stats(db: AsyncSession) -> dict:
    buckets = await db.execute(
        select(
            func.count(ParseRequest.id).label("total"),
            func.avg(ParseRequest.confidence_score).label("avg_conf"),
            func.sum(cast(ParseRequest.confidence_score >= 0.8, Integer)).label("high"),
            func.sum(cast((ParseRequest.confidence_score >= 0.5) & (ParseRequest.confidence_score < 0.8), Integer)).label("medium"),
            func.sum(cast(ParseRequest.confidence_score < 0.5, Integer)).label("low"),
        )
    )
    row = buckets.one()
    method_rows = await db.execute(
        select(ParseRequest.match_method, func.count(ParseRequest.id).label("cnt"))
        .group_by(ParseRequest.match_method)
    )
    return {
        "total_parses":      row.total or 0,
        "avg_confidence":    round(float(row.avg_conf or 0), 3),
        "high_confidence":   int(row.high or 0),
        "medium_confidence": int(row.medium or 0),
        "low_confidence":    int(row.low or 0),
        "by_match_method":   {r.match_method: r.cnt for r in method_rows},
    }


async def save_feedback(
    db: AsyncSession, request_id: int, field_name: str,
    correct_value: str, notes: Optional[str] = None,
) -> ParseFeedback:
    row = ParseFeedback(request_id=request_id, field_name=field_name,
                        correct_value=correct_value, notes=notes)
    db.add(row)
    await db.flush()
    return row


async def get_feedback_for_request(db: AsyncSession, request_id: int) -> list[ParseFeedback]:
    result = await db.execute(
        select(ParseFeedback).where(ParseFeedback.request_id == request_id)
        .order_by(ParseFeedback.created_at)
    )
    return list(result.scalars().all())


async def get_feedback_summary(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(ParseFeedback.field_name, func.count(ParseFeedback.id).label("correction_count"))
        .group_by(ParseFeedback.field_name)
        .order_by(desc("correction_count"))
    )
    return [{"field_name": r.field_name, "correction_count": r.correction_count} for r in result]