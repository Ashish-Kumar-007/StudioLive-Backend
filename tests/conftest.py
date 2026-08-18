import asyncio
from typing import AsyncGenerator, Generator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base_class import Base
from app.db.session import get_db
from app.main import app

# Create a test engine pointing to the database URL configured in env
# Note: For strict safety, a separate test database should be used in production environments
test_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create session-scoped event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create database tables before running test session, and clean up after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for a single test.
    
    Rolls back any modifications made during the test execution.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = TestAsyncSessionLocal(bind=connection)
        
        yield session
        
        await session.close()
        await transaction.rollback()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient for E2E and API testing with overriden DB session dependency."""
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as ac:
        yield ac
        
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def flush_redis():
    """Clear Redis cache before each test to prevent rate limit cross-contamination."""
    from app.modules.auth.rate_limit import redis_client
    try:
        await redis_client.flushdb()
    except Exception:
        pass
    yield
