"""Add src/ to path and initialize logging for all app modules."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from Drug_EDA.logger import LOG_FILEPATH, get_logger, setup_logging  # noqa: E402

setup_logging()

__all__ = ["LOG_FILEPATH", "get_logger", "setup_logging"]
