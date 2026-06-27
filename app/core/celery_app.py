import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "wallet_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.core.tasks"],  # FIX 1: tells Celery where to find tasks
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,  # FIX 2: suppress deprecation warning
)
