from dataclasses import dataclass
from typing import Callable

__all__ = ["Subscription"]


@dataclass
class Subscription:
    channels: set[str]
    handler: Callable[[bytes, dict[str, str]], None]
