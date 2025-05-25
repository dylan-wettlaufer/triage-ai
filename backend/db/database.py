# db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from config.settings import settings
from datetime import datetime, timezone

# Construct the database URL from individual settings
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.PGUSER}:{settings.PGPASSWORD}@"
    f"{settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}"
)


# Use create_async_engine for async database operations
# NO connect_args for SSL here! The sslmode is handled by the URL.
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# Use async_sessionmaker for async sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    