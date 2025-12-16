from app.tasks import celery_app


@celery_app.task
def send_notification(user_id: int, message: str) -> None:
    pass


@celery_app.task
def cleanup_expired_data() -> None:
    pass

