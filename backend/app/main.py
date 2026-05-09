from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import uploads
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.services.document_processing_service import fail_stale_processing_documents


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with SessionLocal() as db:
        fail_stale_processing_documents(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["health"])
    def root() -> dict[str, str]:
        return {
            "app": settings.app_name,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(uploads.router, prefix=settings.api_prefix)
    return app


app = create_app()
