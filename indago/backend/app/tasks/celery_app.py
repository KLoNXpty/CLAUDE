"""
INDAGO Evidence Capture Platform
Celery Application Configuration
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "indago",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.capture_tasks", "app.tasks.scheduler_tasks"],
)

celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
    task_acks_late=True,

    # Task routing
    task_routes={
        "capture.execute_forensic_capture": {"queue": "capture"},
        "capture.generate_report": {"queue": "reports"},
        "scheduler.*": {"queue": "scheduler"},
    },

    # Result settings
    result_expires=86400 * 7,  # 7 days

    # Beat scheduler
    beat_schedule={
        "run-scheduled-captures": {
            "task": "scheduler.run_due_captures",
            "schedule": 60.0,  # Every minute
        },
    },

    # Concurrency
    worker_concurrency=settings.MAX_CONCURRENT_CAPTURES,
)
