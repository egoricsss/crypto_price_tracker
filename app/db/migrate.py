import sys
from alembic.config import Config
from alembic import command

from app.core.logging import setup_logging, get_logger


setup_logging()
logger = get_logger(__name__)


def run_migrations():
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations applied successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
