from typing import TypedDict

__all__ = ["DeadLettersConfig"]


class DeadLettersConfig(TypedDict, total=False):
    exchange_name: str
    routing_key: str
    max_requeue_counter: int
