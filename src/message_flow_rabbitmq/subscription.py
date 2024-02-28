from dataclasses import dataclass
from typing import Any

__all__ = ["Subscription"]


@dataclass
class Subscription:
    channels: set[str]
    handler: Any
