"""
db/models_db.py — SQLAlchemy ORM table definitions.

Tables
──────
1. parse_requests  — every address parsed, linked to the user who parsed it
2. parse_feedback  — user corrections on specific fields
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class ParseRequest(Base):
    __tablename__ = "parse_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Clerk user ID — e.g. "user_2abc123xyz"
    # nullable=True so unauthenticated/dev requests still save
    user_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        comment="Clerk user ID — filters history per user"
    )

    raw_address: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    match_method: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    feedback: Mapped[list["ParseFeedback"]] = relationship(
        "ParseFeedback", back_populates="parse_request",
        cascade="all, delete-orphan", lazy="select",
    )

    def __repr__(self) -> str:
        return f"<ParseRequest id={self.id} user={self.user_id} conf={self.confidence_score:.2f}>"


Index("idx_parse_requests_confidence", ParseRequest.confidence_score)
Index("idx_parse_requests_created_at", ParseRequest.created_at.desc())
Index("idx_parse_requests_user_id", ParseRequest.user_id)


class ParseFeedback(Base):
    __tablename__ = "parse_feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("parse_requests.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    correct_value: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    parse_request: Mapped["ParseRequest"] = relationship("ParseRequest", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<ParseFeedback id={self.id} field={self.field_name}>"


Index("idx_parse_feedback_request_id", ParseFeedback.request_id)
Index("idx_parse_feedback_field_name", ParseFeedback.field_name)