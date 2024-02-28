from typing import TYPE_CHECKING, Callable, Protocol, TypeVar

import pika

if TYPE_CHECKING:
    from ..consumer import RabbitMQConsumer

__all__ = ["IRetryManager"]

Consumer = TypeVar("Consumer", bound="RabbitMQConsumer")

ConnectionProperty = Callable[["RabbitMQConsumer"], pika.BlockingConnection]
Callback = Callable[["RabbitMQConsumer"], None]


class IRetryManager(Protocol):
    def reconnect(self) -> Callable[[ConnectionProperty], ConnectionProperty]:
        ...

    def restart(self, resetter: Callback | None = None) -> Callable[[Callback], Callback]:
        ...
