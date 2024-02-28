from typing import Protocol

from pika.adapters.blocking_connection import BlockingChannel

__all__ = ["IDeadLetters"]


class IDeadLetters(Protocol):
    def is_requeue_needed(self, headers: dict[str, str]) -> bool:
        ...

    def make_arguments(self, channel: BlockingChannel, queue_name: str) -> dict[str, str]:
        ...
