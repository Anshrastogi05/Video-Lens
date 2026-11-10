"""Small reliability helpers shared by the pipeline stages."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_call(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay: float = 1.0,
    backoff: float = 2.0,
    operation_name: str = "operation",
) -> T:
    """Retry transient operations with exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:  # provider/FFmpeg errors vary by dependency
            last_error = exc
            if attempt == attempts:
                break
            delay = initial_delay * (backoff ** (attempt - 1))
            print(f"{operation_name} failed (attempt {attempt}/{attempts}); retrying in {delay:.1f}s")
            time.sleep(delay)
    raise RuntimeError(f"{operation_name} failed after {attempts} attempts") from last_error
