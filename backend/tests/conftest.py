"""Pytest fixtures for backend tests."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Set MPLCONFIGDIR early to avoid cache issues in sandbox
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

from app.core.security import limiter
from app.db.session import get_session
from app.main import app
from app.services.registry import registry


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset SlowAPI rate limit storage between tests."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(scope="session", autouse=True)
def init_test_registry():
    """Ensure registry is initialized once for test session."""
    registry.startup()
    yield


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database session for isolated testing."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a FastAPI TestClient with database session override."""
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        yield client
    app.dependency_overrides.clear()
