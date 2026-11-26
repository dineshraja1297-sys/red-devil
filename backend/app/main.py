"""FastAPI entry point.  Run from the project root:

    uvicorn backend.app.main:app --reload
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import auth, health
from backend.app.core.errors import register_error_handlers
from backend.app.core.logging_config import setup_logging
from config.settings import get_settings

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s v%s (env=%s, trading_mode=%s, live_trading_enabled=%s)",
             settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT,
             settings.TRADING_MODE, settings.LIVE_TRADING_ENABLED)
    yield
    log.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Red Devil is a multi-agent trading platform. **Stage 1: paper mode only; live trading is locked.**",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    log.info("%s %s -> %s (%.1f ms) rid=%s", request.method, request.url.path,
             response.status_code, elapsed, request_id)
    return response


register_error_handlers(app)
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
