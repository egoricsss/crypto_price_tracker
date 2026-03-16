from celery import Celery, signals

from app.core.config import settings
from app.core.logging import setup_logging, get_logger

# Инициализируем логирование для воркера
setup_logging()
logger = get_logger(__name__)

# Создаём приложение Celery
celery_app = Celery(
    "crypto_price_tracker",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=["app.workers.tasks"],
)

# Конфигурация Celery
celery_app.conf.update(
    # Сериализация
    task_serializer=settings.celery.task_serializer,
    result_serializer=settings.celery.result_serializer,
    accept_content=settings.celery.accept_content,
    # Таймауты
    task_time_limit=300,  # 5 минут максимум на задачу
    task_soft_time_limit=240,  # 4 минуты мягкий лимит
    # Retry настройки
    task_acks_late=True,  # Подтверждение задачи после выполнения
    task_reject_on_worker_lost=True,  # Повтор при падении воркера
    # Часовой пояс
    timezone=settings.celery.timezone,
    enable_utc=settings.celery.enable_utc,
    # Периодические задачи (Celery Beat)
    beat_schedule={
        "fetch-crypto-prices-every-minute": {
            "task": "app.workers.tasks.fetch_prices_task",
            "schedule": settings.celery.fetch_price_interval,  # 60 секунд
            "options": {"queue": "default"},
        },
    },
)


# Логирование событий Celery
@signals.worker_process_init.connect
def worker_init_handler(**kwargs):
    logger.info("Celery worker process initialized")


@signals.worker_process_shutdown.connect
def worker_shutdown_handler(**kwargs):
    logger.info("Celery worker process shutting down")


@signals.task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    logger.info(f"Task {task.name}[{task_id}] started")


@signals.task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    logger.info(f"Task {task.name}[{task_id}] completed")
