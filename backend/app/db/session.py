"""Database session management with SQLite."""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Ensure sqlite storage directory exists
db_file_path = settings.DATABASE_URL.replace("sqlite:///", "")
Path(db_file_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    """Create all SQLModel tables on startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    with Session(engine) as session:
        yield session
