import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort first-boot bootstrap. Skipped in tests via env var so the
    # in-memory test DB isn't competing with the production-bound SessionLocal.
    if os.getenv("SKIP_STARTUP_BOOTSTRAP") != "1":
        try:
            from app.database import SessionLocal
            from app.services.bootstrap import ensure_initial_admin

            with SessionLocal() as db:
                ensure_initial_admin(db)
        except Exception as e:
            log.warning("startup bootstrap skipped: %s", e)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TwinVal Field Observation Portal",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.routers import (
        admin,
        auth,
        observations,
        owner_profiles,
        properties,
        sensor_zones,
    )

    # slowapi limiter — share between auth router (already attached) and app
    app.state.limiter = auth.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.include_router(auth.router)
    app.include_router(owner_profiles.router)
    app.include_router(properties.router)
    app.include_router(sensor_zones.router)
    app.include_router(observations.router)
    app.include_router(admin.router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    @app.exception_handler(ValueError)
    async def value_error_handler(_request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app


app = create_app()
