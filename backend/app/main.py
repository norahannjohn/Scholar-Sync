from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.collectors.registry_defaults import ensure_official_registry_seeded
from app.core.config import configure_logging, get_settings
from app.db.session import SessionLocal
from app.services.auth_service import ensure_initial_admin_from_env

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.app_env != "test":
        try:
            with SessionLocal() as db:
                if ensure_initial_admin_from_env(db):
                    logger.info("Initial administrator account ensured from environment.")
                src_count, sch_count = ensure_official_registry_seeded(db)
                if src_count or sch_count:
                    logger.info(
                        "Registered %d official sources and %d verified schemes.",
                        src_count,
                        sch_count,
                    )
        except Exception as exc:
            logger.warning("Startup DB bootstrap skipped (%s): %s", type(exc).__name__, exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    def root_health():
        return {"status": "ok"}

    # Single-service Render deployment: serve built React SPA if frontend/dist exists
    repo_root = Path(__file__).resolve().parents[3]
    dist_dir = repo_root / "frontend" / "dist"
    if dist_dir.is_dir():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        index_html = dist_dir / "index.html"

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="API route not found.")
            candidate = (dist_dir / full_path).resolve()
            if full_path and candidate.is_file() and str(candidate).startswith(str(dist_dir.resolve())):
                return FileResponse(str(candidate))
            return FileResponse(str(index_html))
    else:
        @app.get("/")
        def root_info():
            return JSONResponse(
                {
                    "app": settings.app_name,
                    "api_prefix": settings.api_v1_prefix,
                    "health": f"{settings.api_v1_prefix}/health",
                }
            )

    return app


app = create_app()
