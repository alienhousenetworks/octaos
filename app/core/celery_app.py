from celery import Celery
from app.core.config import settings
import os

broker_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
if os.getenv("TESTING"):
    broker_url = "memory://"

celery_app = Celery("worker", broker=broker_url)

celery_app.conf.task_routes = {
    "app.worker.tasks.*": "main-queue",
}

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "daily-autonomous-operations": {
        "task": "run_daily_operations",
        "schedule": crontab(hour=8, minute=0),
    },
    "poll-workflows": {
        "task": "poll_and_execute_workflows",
        "schedule": crontab(minute="*"),
    },
    "publish-scheduled-posts": {
        "task": "publish_scheduled_posts",
        "schedule": crontab(minute="*/5"),
    },
    "sales-meeting-reminders": {
        "task": "send_sales_meeting_reminders",
        "schedule": crontab(minute="*/5"),
    },
    "poll-gmail-sales-inbox": {
        "task": "poll_gmail_sales_inbox",
        "schedule": crontab(minute="*/3"),
    },
}

if os.getenv("TESTING"):
    celery_app.conf.task_always_eager = True
