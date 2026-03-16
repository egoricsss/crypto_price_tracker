from app.workers.celery_app import celery_app
from app.workers.tasks import fetch_prices_task

__all__ = ["celery_app", "fetch_prices_task"]
