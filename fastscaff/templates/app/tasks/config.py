from app.core.config import settings


class CeleryConfig:
    broker_url = settings.CELERY_BROKER_URL
    result_backend = settings.CELERY_RESULT_BACKEND
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = settings.CELERY_TIMEZONE
    enable_utc = True
    task_track_started = True
    task_time_limit = 30 * 60
    worker_prefetch_multiplier = 1
    broker_connection_retry_on_startup = True

    beat_schedule = {
        # Example scheduled task (uncomment to enable):
        # "cleanup-every-hour": {
        #     "task": "app.tasks.jobs.example.cleanup_expired_data",
        #     "schedule": 3600.0,
        # },
    }


celery_config = CeleryConfig()

