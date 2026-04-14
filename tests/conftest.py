import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("adminpass"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(db: AsyncSession) -> User:
    user = User(
        email="user@example.com",
        hashed_password=hash_password("userpass"),
        role=UserRole.USER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpass"},
    )
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client: AsyncClient, normal_user: User) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "userpass"},
    )
    return resp.json()["access_token"]
