"""Simple logging configuration for the application.

Provides a `setup_logging` helper that configures a console and optional
file handler, plus a small `get_logger` helper for modules to obtain
loggers consistently.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, List

LOG_FILE: Path = Path(__file__).resolve().parent.parent / "app.log"


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = LOG_FILE) -> None:
    """Configure the root logger with console and optional file handlers.

    Uses `force=True` to ensure the configuration replaces prior handlers
    (useful when running inside Streamlit which may preconfigure logging).

    Args:
        level: Logging level (default: logging.INFO).
        log_file: Optional Path to a log file. If the path is writable, a
            FileHandler will be added.
    """
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file is not None:
        try:
            # Ensure the parent folder exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
        except Exception:
            # Best-effort: if file cannot be created, fall back to console only.
            pass

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )


def get_logger(name: str):
    """Return a module logger with the given name.

    Modules should call `get_logger(__name__)` to obtain a logger instance.
    """
    return logging.getLogger(name)


def tail_log_lines(n: int = 200) -> List[str]:
    """Return the last `n` lines from the configured log file.

    If the log file does not exist, an empty list is returned.
    """
    if not LOG_FILE.exists():
        return []
    # Read file efficiently from the end
    with LOG_FILE.open("rb") as f:
        f.seek(0, 2)
        end = f.tell()
        size = 1024
        data = b""
        while end > 0 and data.count(b"\n") <= n:
            read_size = min(size, end)
            f.seek(end - read_size)
            chunk = f.read(read_size)
            data = chunk + data
            end -= read_size
            if end == 0:
                break
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-n:]
