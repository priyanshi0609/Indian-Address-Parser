"""
db/database.py — Async SQLAlchemy engine and session setup.

How it works
────────────
1. create_async_engine() creates ONE engine for the whole app lifetime.
   The engine manages a connection pool — it doesn't open a new DB
   connection for every request; it reuses existing ones.

2. async_sessionmaker() creates a factory that produces AsyncSession
   objects. Each request gets its own session from this factory.

3. get_db() is a FastAPI dependency. It creates a session, hands it
   to the route function, and closes it when the request is done —
   even if the route raises an exception.

4. init_db() creates all tables on startup if they don't exist yet.
   In production you'd use Alembic migrations instead, but for
   development this is simpler.

Connection string (from .env):
    postgresql+asyncpg://user:password@host:port/dbname
    ↑ asyncpg is the async PostgreSQL driver (faster than psycopg2)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import logger

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://parser_user:parser_pass@localhost:5432/address_parser",
)

# ── Engine ────────────────────────────────────────────────────────────────────
# echo=False in production — set to True only for debugging SQL queries
# pool_pre_ping=True: test connections before using them (handles DB restarts)
# pool_size=10: keep 10 connections open (reuse across requests)
# max_overflow=20: allow 20 extra connections under heavy load

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ── Session factory ───────────────────────────────────────────────────────────
# expire_on_commit=False: keep ORM objects usable after commit
# (important in async — we don't want implicit lazy-loads after commit)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Declarative Base ──────────────────────────────────────────────────────────
# All SQLAlchemy table models inherit from this Base.
# Base.metadata knows about every table defined in models_db.py.

class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async DB session for a single request.

    Usage in a route:
        @app.post("/parse")
        async def parse(db: AsyncSession = Depends(get_db)):
            await crud.save_parse_request(db, ...)

    The session is automatically closed when the route finishes,
    whether it succeeds or raises an exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()        # commit if no exception
        except Exception:
            await session.rollback()      # rollback on error
            raise


# ── Table creation (used on startup) ─────────────────────────────────────────
async def init_db() -> None:
    """
    Create all tables defined in models_db.py if they don't exist.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS
    via checkfirst=True behaviour in SQLAlchemy.

    In production: replace this with Alembic migrations.
    """
    # Import models so Base.metadata knows about the tables
    from db import models_db  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables verified / created.")


async def close_db() -> None:
    """Dispose the engine connection pool on shutdown."""
    await engine.dispose()
    logger.info("Database engine disposed.")