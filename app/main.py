"""
Sentinel Financial Ecosystem — app/main.py
==========================================
Production-grade entrypoint.

Key fixes vs. the inherited baseline
--------------------------------------
1. TELEMETRY  — setup_tracing() is called inside a try/except block so that a
   missing / unreachable Tempo container can NEVER block or crash the service.
   Tracing degrades gracefully to a no-op; the API remains fully operational.

2. DB STARTUP — The synchronous `time.sleep` retry loop has been replaced with
   an async retry coroutine registered via the modern `lifespan` context manager
   (FastAPI 0.93+). `asyncio.sleep` yields control back to the event loop between
   attempts so Uvicorn's I/O listener is never frozen.

3. DEPRECATED HOOK — `@app.on_event("startup")` is deprecated; replaced with
   the `lifespan` async context manager pattern, which is the current FastAPI
   recommendation and compatible with Starlette's ASGI lifecycle.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from prometheus_client import make_asgi_app
from sqlalchemy.exc import OperationalError

from app import models
from app.api.endpoints import users, wallet
from app.core.logging_config import logger
from app.database import engine
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.tracing import setup_tracing

# ---------------------------------------------------------------------------
# Async, non-blocking database initialisation
# ---------------------------------------------------------------------------

_DB_RETRIES = 5
_DB_RETRY_DELAY_S = 2.0


async def _init_db() -> None:
    """
    Create all ORM-mapped tables, retrying up to _DB_RETRIES times.

    Uses asyncio.sleep so the event loop remains unblocked between attempts —
    Uvicorn can continue accepting connections while we wait for Postgres to
    become ready (common during cold docker-compose starts).
    """
    for attempt in range(1, _DB_RETRIES + 1):
        try:
            logger.info("DB init attempt %d/%d …", attempt, _DB_RETRIES)
            # create_all is synchronous; run it in a thread-pool executor so
            # it does not block the event loop either.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: models.Base.metadata.create_all(bind=engine),
            )
            logger.info("Database schema ready.")
            return
        except OperationalError as exc:
            if attempt == _DB_RETRIES:
                logger.critical(
                    "Database unreachable after %d attempts. "
                    "Continuing startup — endpoints requiring DB will return 503.",
                    _DB_RETRIES,
                )
                return
            logger.warning(
                "Database not ready (attempt %d/%d): %s — retrying in %.0fs …",
                attempt,
                _DB_RETRIES,
                exc.orig,
                _DB_RETRY_DELAY_S,
            )
            await asyncio.sleep(_DB_RETRY_DELAY_S)


# ---------------------------------------------------------------------------
# Application lifespan (replaces deprecated @app.on_event hooks)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ASGI lifespan context manager.

    Everything before `yield` runs on startup; everything after runs on shutdown.
    """
    # --- Startup ---
    logger.info("Sentinel Financial Ecosystem starting up …")
    await _init_db()
    logger.info("Startup complete. Service is accepting requests.")

    yield  # <-- application runs here

    # --- Shutdown ---
    logger.info("Sentinel Financial Ecosystem shutting down …")
    # Add any graceful-shutdown logic here (flush caches, close pools, etc.)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sentinel Financial Ecosystem",
    description="A secure fintech backend with microservices integration.",
    version="1.0.0",
    lifespan=lifespan,
)

security_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Tracing — DEFENSIVE: if Tempo is offline this must NOT block or crash startup
# ---------------------------------------------------------------------------

try:
    setup_tracing(app)
    logger.info("OpenTelemetry tracing initialised successfully.")
except Exception as tracing_exc:  # noqa: BLE001
    # Tempo may be absent in local / CI environments. We log the failure and
    # continue — traces are lost but the service is fully operational.
    logger.warning(
        "OpenTelemetry tracing could not be initialised and will be disabled. "
        "Reason: %s. "
        "To restore tracing, ensure the 'tempo' service is running and "
        "reachable on port 4317.",
        tracing_exc,
    )

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(IdempotencyMiddleware)

# ---------------------------------------------------------------------------
# Prometheus metrics scrape endpoint
# ---------------------------------------------------------------------------

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(wallet.router, prefix="/wallets", tags=["Wallets"])

# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
def root():
    return {
        "status": "Online",
        "service": "Sentinel Financial API",
        "documentation": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Lightweight liveness probe for load-balancers and orchestrators."""
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )