import time
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from app.database import engine
from app import models
from app.api.endpoints import users, wallet 
from app.middleware.tracing import TracingMiddleware
from app.core.logging_config import logger # Use our new structured logger
from fastapi import FastAPI
from app.middleware.idempotency import IdempotencyMiddleware
from app.middleware.tracing import setup_tracing
from prometheus_client import make_asgi_app
# 1. Initialize FastAPI First
app = FastAPI(
    title="Sentinel Financial Ecosystem", 
    description="A secure fintech backend with microservices integration.",
    version="1.0.0"
)

# Initialize OpenTelemetry Tracing
setup_tracing(app)
# 2. Register Middleware (Must happen AFTER app initialization)
app.add_middleware(TracingMiddleware)
# Add the idempotency shield right into the lifecycle
app.add_middleware(IdempotencyMiddleware)
metrics_app=make_asgi_app()
app.mount("/metrics", metrics_app)
# 3. Database Startup Event (Resilience Logic)
@app.on_event("startup")
def startup_event():
    retries = 5
    while retries > 0:
        try:
            logger.info("Attempting to connect to the database...")
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database connected successfully!")
            break
        except OperationalError as e:
            retries -= 1
            logger.warning(f"Database not ready ({e}). Retrying in 2s... ({retries} left)")
            time.sleep(2)
    
    if retries == 0:
        logger.error("CRITICAL: Could not connect to database. Service may fail.")

# 4. Include Routers
# Using prefixes here keeps the individual router files clean.
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])

@app.get("/", tags=["Health"])
def root():
    # --- ADD THIS LINE ---
    logger.info("The root endpoint was accessed!") 
    # ---------------------
    return {
        "status": "Online",
        "service": "Sentinel Financial API",
        "documentation": "/docs"
    }

# 6. Global Exception Handler (Observability)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # This will now include the [TX-ID] because of our TracingMiddleware
    logger.error(f"Global error caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Reference the transaction ID in headers."}
    )