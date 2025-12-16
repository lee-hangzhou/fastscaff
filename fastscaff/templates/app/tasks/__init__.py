from celery import Celery

from app.tasks.config import celery_config

celery_app = Celery("tasks")
celery_app.config_from_object(celery_config)
celery_app.autodiscover_tasks(["app.tasks.jobs"])

__all__ = ["celery_app"]

