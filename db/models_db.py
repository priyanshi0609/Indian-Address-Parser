"""
db/models_db.py — SQLAlchemy ORM table definitions.

Two tables:

1. parse_requests
   ─────────────
   Every address that comes into the API gets a row here.
   The full parsed result is stored as JSONB — one column holds
   all 12+ fields. This avoids 12 nullable columns while keeping
   the data queryable via PostgreSQL's JSONB operators.

2. parse_feedback
   ──────────────
   When a user tells us "city should be Lucknow, not Kanpur",
   that correction is stored here. It's linked back to the
   original parse_request row via foreign key.
   Over time, this builds a dataset of known errors that can
   be used to measure and improve accuracy.

Why JSONB for parsed_output?
────────────────────────────
The parsed address has ~12 optional fields. If we made each
field a column, every row would have many NULL values and
any schema change (adding a new field) needs an ALTER TABLE.

JSONB stores the dict directly and is still queryable:
    WHERE parsed_output->>'city' = 'Delhi'
    WHERE (parsed_output->>'confidence_score')::float > 0.8

The trade-off: you lose SQL type enforcement on the JSON fields.
We accept this because the Python layer (Pydantic) already
validates the structure before it reaches the DB.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# Table 1 — parse_requests
# ─────────────────────────────────────────────────────────────────────────────

class ParseRequest(Base):
    """
    One row per address parsed through the API.

    Columns
    ───────
    id              Auto-incrementing primary key (BigInteger for millions of rows)
    raw_address     The exact string the user submitted — never modified
    parsed_output   Full parsed result as JSONB dict
    confidence_score  Float 0.0–1.0, duplicated from JSONB for fast filtering
    match_method    How city/state was resolved: 'pincode'|'exact'|'fuzzy'|'none'
    created_at      When the parse happened (stored as UTC)

    Why store confidence_score as a separate column AND inside JSONB?
    ─────────────────────────────────────────────────────────────────
    JSONB field queries like (parsed_output->>'confidence_score')::float
    are slower than querying a native FLOAT column. Since "find all
    low-confidence parses" is a very common query, having it as a real
    column makes that query fast with a simple B-tree index.
    """

    __tablename__ = "parse_requests"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    raw_address: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Original unmodified address string"
    )
    parsed_output: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="Full parsed result — all 12+ fields"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Duplicated from JSONB for fast indexed queries"
    )
    match_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none",
        comment="How city/state was resolved: pincode|exact|fuzzy|state_abbr|none"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),    # DB sets this, not Python — consistent across timezones
        nullable=False,
    )

    # Relationship — one parse can have many feedback entries
    feedback: Mapped[list["ParseFeedback"]] = relationship(
        "ParseFeedback",
        back_populates="parse_request",
        cascade="all, delete-orphan",   # delete feedback if parse is deleted
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<ParseRequest id={self.id} "
            f"confidence={self.confidence_score:.2f} "
            f"method={self.match_method}>"
        )


# ── Indexes on parse_requests ─────────────────────────────────────────────────

# Index 1: Filter by confidence score (most common analytics query)
# "Show me all parses with confidence < 0.5"
Index(
    "idx_parse_requests_confidence",
    ParseRequest.confidence_score,
)

# Index 2: Time-range queries, always descending (most recent first)
# "Show me parses from the last 24 hours"
Index(
    "idx_parse_requests_created_at",
    ParseRequest.created_at.desc(),
)

# Index 3: Filter by match method
# "How many parses used pincode vs fuzzy matching?"
Index(
    "idx_parse_requests_match_method",
    ParseRequest.match_method,
)


# ─────────────────────────────────────────────────────────────────────────────
# Table 2 — parse_feedback
# ─────────────────────────────────────────────────────────────────────────────

class ParseFeedback(Base):
    """
    User-submitted correction on a specific parsed field.

    Example: Parse #42 extracted city='Kanpur' but the correct city
    is 'Lucknow'. The user submits:
        { request_id: 42, field_name: 'city', correct_value: 'Lucknow' }

    This table powers:
    1. Accuracy measurement — compare correct_value against what was parsed
    2. Edge case discovery — recurring corrections point to patterns
       the regex missed
    3. Future ML training data — labelled corrections are ground truth

    Columns
    ───────
    id              Auto-incrementing primary key
    request_id      FK → parse_requests.id (which parse was wrong)
    field_name      Which field was incorrect: 'city', 'state', 'locality', etc.
    correct_value   What the value should have been
    notes           Optional free-text explanation from the user
    created_at      When the feedback was submitted
    """

    __tablename__ = "parse_feedback"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("parse_requests.id", ondelete="CASCADE"),
        nullable=False,
        comment="Which parse request this feedback is about",
    )
    field_name: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Which field was wrong: city|state|locality|house_number|etc."
    )
    correct_value: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="What the correct value should be"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional explanation from the user"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship — back to the parse request
    parse_request: Mapped["ParseRequest"] = relationship(
        "ParseRequest", back_populates="feedback"
    )

    def __repr__(self) -> str:
        return (
            f"<ParseFeedback id={self.id} "
            f"request_id={self.request_id} "
            f"field={self.field_name} "
            f"correct='{self.correct_value}'>"
        )


# ── Indexes on parse_feedback ──────────────────────────────────────────────────

# Index: look up all feedback for a specific parse request
Index(
    "idx_parse_feedback_request_id",
    ParseFeedback.request_id,
)

# Index: find all corrections for a specific field name
# "How often is 'city' wrong vs 'state'?"
Index(
    "idx_parse_feedback_field_name",
    ParseFeedback.field_name,
)