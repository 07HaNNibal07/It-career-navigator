import os
import asyncio

os.environ["DB_URL"] = "sqlite+aiosqlite:///./test_api.db"
os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest"
os.environ["INTERNAL_API_KEY"] = "test-internal-key"

from httpx import ASGITransport, AsyncClient
import pytest

from it_career_navigator.main import app
from it_career_navigator.database import Base, get_db
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool



pytest_plugins = ["anyio"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def test_engine():
    return create_async_engine(
        os.environ["DB_URL"],
        poolclass=NullPool,
    )


@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession, None]:
    connection = await test_engine.connect()
    transaction = await connection.begin()

    TestSession = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with TestSession() as session:
        yield session

    await transaction.rollback()
    await connection.close()


@pytest.fixture
async def client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()