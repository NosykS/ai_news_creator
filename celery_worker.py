#celery_worker.py
from celery import Celery
from celery.schedules import crontab
from app.config import settings
from app.utils import setup_logging

setup_logging()

celery_app = Celery(
    "ai_news_bot",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
)

celery_app.conf.beat_schedule = {
    "parse-sites-every-30-minutes": {
        "task": "app.tasks.parse_sites_task",
        "schedule": crontab(minute="*/30"),
    },
    "parse-telegram-every-30-minutes": {
        "task": "app.tasks.parse_telegram_task",
        "schedule": crontab(minute="*/30"),
    },
}