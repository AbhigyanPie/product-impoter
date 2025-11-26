"""
Celery Configuration
--------------------
Celery app setup for async task processing.
"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "product_importer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task result expiration (1 hour)
    result_expires=3600,
    # Task acknowledgment
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Limit prefetch to process one task at a time for progress tracking
    worker_prefetch_multiplier=1,
)