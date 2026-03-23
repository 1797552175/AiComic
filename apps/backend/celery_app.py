"""
Celery 异步任务配置
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "aicomic",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.shot_tasks",
        "tasks.compose_tasks",
    ]
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
