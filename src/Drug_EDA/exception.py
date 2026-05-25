import sys
from typing import Any


class customexception(Exception):
    """Wraps an exception with script name, line number, and message."""

    def __init__(self, error_message: Any, error_details: Any = sys):
        self.error_message = error_message
        exc_type, exc_value, exc_tb = error_details.exc_info()
        if exc_tb is None:
            self.lineno = 0
            self.file_name = "unknown"
        else:
            self.lineno = exc_tb.tb_lineno
            self.file_name = exc_tb.tb_frame.f_code.co_filename

    def __str__(self) -> str:
        return (
            "Error occured in python script name [{0}] line number [{1}] "
            "error message [{2}]"
        ).format(self.file_name, self.lineno, str(self.error_message))


def raise_custom(error: Exception) -> None:
    """Re-raise as customexception preserving the original traceback context."""
    raise customexception(error, sys) from error


def format_error(exc: BaseException) -> str:
    """User-facing error string (detailed for customexception)."""
    if isinstance(exc, customexception):
        return str(exc)
    return f"{type(exc).__name__}: {exc}"


if __name__ == "__main__":
    try:
        _ = 1 / 0
    except Exception as e:
        raise_custom(e)
