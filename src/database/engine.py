"""Database engine and session factory for SQLAlchemy async ORM."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.core.config import Config


# Create async engine
# Note: psycopg2 URLs need to be converted to asyncpg:
# postgresql:// -> postgresql+asyncpg://
async_db_url = Config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    async_db_url,
    echo=False,  # Set to True for SQL debugging
    future=True,
    poolclass=NullPool,  # Use NullPool for async (no connection pooling at SQLAlchemy level)
    # asyncpg handles its own connection pooling internally
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get a database session.

    Usage in routes:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database by creating all tables."""
    async with engine.begin() as conn:
        # Import all models here to register them with Base.metadata
        from src.database.models.base import Base  # noqa: F401
        from src.database import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose of the engine and close all connections."""
    await engine.dispose()
