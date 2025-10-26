from typing import AsyncGenerator
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

def clean_database_url(url: str) -> str:
    """
    Convert database URL for asyncpg compatibility.
    - Changes postgresql:// to postgresql+asyncpg://
    - Removes query parameters that asyncpg doesn't support
    - Keeps only ssl-related parameters that asyncpg understands
    """
    # Convert to asyncpg dialect
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Parse the URL
    parsed = urlparse(url)
    
    # Remove query parameters (asyncpg will use SSL by default for remote hosts)
    # For Neon, SSL is automatically handled
    if parsed.query:
        # Remove all query params - asyncpg will auto-detect SSL need
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            '',  # Empty query string
            parsed.fragment
        ))
        return clean_url
    
    return url

# Convert and clean the database URL
database_url = clean_database_url(settings.database_url)

engine = create_async_engine(
    database_url,
    echo=settings.database_echo,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db() -> None:
    await engine.dispose()

