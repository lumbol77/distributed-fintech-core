from fastapi import FastAPI
import logging
import time
from sqlalchemy.exc import OperationalError

# --- UPDATED IMPORTS ---
from app.database import engine
from app import models
# Import from the new location we created
from app.api.endpoints import users, wallet 
# 1. Setup Professional Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 2. Initialize FastAPI
app = FastAPI(
    title="Sentinel Financial Ecosystem", 
    description="A secure fintech backend with microservices integration.",
    version="1.0.0"
)

# 3. Database Startup Event
@app.on_event("startup")
def startup_event():
    retries = 5
    while retries > 0:
        try:
            logger.info("Attempting to connect to the database...")
            models.Base.metadata.create_all(bind=engine)
            logger.info("Database connected successfully!")
            break
        except OperationalError:
            retries -= 1
            logger.warning(f"Database not ready. Retrying in 2 seconds... ({retries} retries left)")
            time.sleep(2)
    
    if retries == 0:
        logger.error("Could not connect to the database. Exiting.")

# 4. Include Routers (With Corrected Prefixes)
# This is the "Control Center" for your URLs.
# Note: Ensure you removed prefix="/wallet" from wallet.py and prefix="/users" from users.py
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])

# 5. Root Health Check
@app.get("/")
def root():
    return {
        "status": "Online",
        "service": "Sentinel Financial API",
        "documentation": "/docs"
    }

# 6. Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global error caught: {exc}")
    return {"detail": "An internal server error occurred. Please check logs."}