from typing import TypedDict

__all__ = ["RetryConfig"]


class RetryConfig(TypedDict, total=False):
    min_delay: float
    max_delay: float
    max_retries: int
    backoff: float
    jitter: float | tuple[float, float]
    reconnect_on: tuple[type[Exception], ...]
