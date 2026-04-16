from __future__ import annotations

import logging
from pathlib import Path


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)


def get_logger(
    *,
    logger_name: str = "bpcl_delivery_sheet_generator",
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: str | Path | None = None,
) -> logging.Logger:
    """
    Create or return a package-wide logger with consistent formatting.

    Notes:
    - Reuses the same logger instance if already configured.
    - Adds console logging by default.
    - Adds file logging only when explicitly requested.
    """

    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_to_file:
        if not log_file_path:
            raise ValueError(
                "log_file_path must be provided when log_to_file is True."
            )

        file_path = Path(log_file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger