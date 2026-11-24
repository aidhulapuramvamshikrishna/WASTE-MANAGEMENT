"""Application configuration for EcoSort Backend."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_repo_root() -> Path:
    # app/config.py -> app -> backend -> repo root
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "ml").is_dir() and (parent / "backend").is_dir():
            return parent
    return current.parent.parent


REPO_ROOT = _resolve_repo_root()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENV: str = "development"
    PROJECT_NAME: str = "EcoSort API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Paths
    REPO_ROOT_DIR: Path = REPO_ROOT
    MODEL_DIR: str = str(REPO_ROOT / "ml" / "artifacts")
    STORAGE_DIR: str = str(REPO_ROOT / "backend" / "storage")
    CLASSES_JSON_PATH: str = str(REPO_ROOT / "data" / "processed" / "waste12" / "classes.json")
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT / 'backend' / 'storage' / 'ecosort.db'}"

    # Model Serving
    DEFAULT_MODEL: str = "mobilenet_v3"
    TORCH_DEVICE: str = "auto"  # auto | cpu | mps | cuda

    # Security & Upload Limits (SECURITY.md §1)
    MAX_UPLOAD_MB: int = 8
    MAX_IMAGE_PIXELS: int = 40_000_000
    RATE_LIMIT_PREDICT: str = "20/minute"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()

# Ensure storage directories exist
os.makedirs(Path(settings.STORAGE_DIR) / "uploads", exist_ok=True)
os.makedirs(Path(settings.STORAGE_DIR) / "gradcam", exist_ok=True)
