import logging
import os
from datetime import datetime
from pathlib import Path

# Project root: d:\i (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_FILEPATH = str(LOG_DIR / LOG_FILE)

_LOG_FORMAT = "[%(asctime)s] %(lineno)d %(name)s - %(levelname)s - %(message)s"
_CONFIGURED = False


def setup_logging(level: int = logging.DEBUG) -> str:
    """Configure file + console logging once per process. Returns log file path."""
    global _CONFIGURED
    if _CONFIGURED:
        return LOG_FILEPATH

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = logging.FileHandler(LOG_FILEPATH, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("Logging initialized. Log file: %s", LOG_FILEPATH)
    return LOG_FILEPATH


def get_logger(name: str) -> logging.Logger:
    """Return a named logger; ensures setup_logging() has run."""
    setup_logging()
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("Logger test OK")
