from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Engine configuration tailored for SQLite (local) and Supabase (cloud)
engine_kwargs = {"echo": False, "future": True}

if "sqlite" in settings.DATABASE_URL:
    db_file_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    Path(db_file_path).parent.mkdir(parents=True, exist_ok=True)
else:
    # PostgreSQL / Supabase Transaction Pooler configuration
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }

# Universal Async SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for all 13 database tables
class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency helper to yield an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
