"""Console + rotating file logging — this runs unattended for hours/days, so
a persisted log matters more than scrollback."""

import logging
from logging.handlers import RotatingFileHandler

import config


def setup_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        config.LOG_FILE_PATH, maxBytes=config.LOG_MAX_BYTES, backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
