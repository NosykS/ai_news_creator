#db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

POSTGRES_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.PG_USERNAME}:{settings.PG_PASSWORD}"
    f"@{settings.PG_URL}/{settings.PG_NAME}"
)

POSTGRES_SYNC_URL = (
    f"postgresql+psycopg2://{settings.PG_USERNAME}:{settings.PG_PASSWORD}"
    f"@{settings.PG_URL}/{settings.PG_NAME}"
)
postgres_engine = create_async_engine(POSTGRES_DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(postgres_engine, expire_on_commit=False, autoflush=False)

postgres_sync = create_engine(POSTGRES_SYNC_URL, echo=True)
SyncSessionLocal = sessionmaker(postgres_sync, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session