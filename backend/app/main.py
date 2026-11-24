"""FastAPI application entrypoint for EcoSort."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.endpoints import router as api_v1_router
from app.config import settings
from app.core.security import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    limiter,
)
from app.db.session import init_db
from app.services.registry import registry


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle."""
    # 1. Initialize SQLite tables
    init_db()

    # 2. Discover models and eagerly load default model (mobilenet_v3)
    registry.startup()

    yield


def create_app() -> FastAPI:
    """Application factory for EcoSort FastAPI backend."""
    is_production = settings.ENV.lower() == "production"

    app_instance = FastAPI(
        title=settings.PROJECT_NAME,
        description="Municipal Waste Classification API with PyTorch CNN inference & Grad-CAM explanations",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )

    # Attach rate limiter state
    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Middlewares (order: request_id first, then security headers, then CORS)
    app_instance.add_middleware(SecurityHeadersMiddleware)
    app_instance.add_middleware(RequestIDMiddleware)

    if settings.ALLOWED_ORIGINS:
        app_instance.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # Standardized error response handler (ARCHITECTURE §5.1)
    @app_instance.exception_handler(HTTPException)
    async def custom_http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "request_id": request_id,
                }
            },
        )

    @app_instance.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Internal server error.",
                    "request_id": request_id,
                }
            },
        )

    # Mount API V1 routes
    app_instance.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app_instance


app = create_app()
