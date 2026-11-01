from celery import Celery

# SQLite database ko hi Celery ka broker bana lete hain, koi extra package nahi chahiye!
celery_app = Celery(
    "plix",
    broker="sqla+sqlite:///./plix.db",
    backend="db+sqlite:///./plix.db"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)