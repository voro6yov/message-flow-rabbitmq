import functools
import logging
import time
from random import uniform
from typing import TYPE_CHECKING, Callable, TypeVar

import pika

from .reconnecting_error import ReconnectingError
from .retry_config import RetryConfig

if TYPE_CHECKING:
    from ..consumer import RabbitMQConsumer
    from ..producer import RabbitMQProducer

__all__ = ["RetryManager"]

Client = TypeVar("Client", "RabbitMQConsumer", "RabbitMQProducer")

ConnectionProperty = Callable[[Client], pika.BlockingConnection]
Callback = Callable[[Client], None]


class RetryManager:
    def __init__(self, config: RetryConfig) -> None:
        self._min_delay = config.get("min_delay", 0.1)
        self._max_delay = config.get("max_delay", 300)
        self._max_retries = config.get("max_retries", 10)
        self._backoff = config.get("backoff", 2.7)
        self._jitter = config.get("jitter", (0.1, 0.9))
        self._reconnect_on = config.get("reconnect_on", (Exception,))

        self._logger = logging.getLogger(__name__)

    def reconnect(self) -> Callable[[ConnectionProperty], ConnectionProperty]:
        def recalculate_tries(counter: int) -> int:
            counter -= 1

            if not counter:
                raise ReconnectingError("Retries are exceeded.")

            return counter

        def recalculate_delay(delay: float) -> float:
            delay *= self._backoff
            delay += uniform(*self._jitter) if isinstance(self._jitter, tuple) else self._jitter

            if self._max_delay is not None:
                delay = min(delay, self._max_delay)

            return delay

        def decorator(connection_property: ConnectionProperty) -> ConnectionProperty:
            @functools.wraps(connection_property)
            def wrapper(consumer: "RabbitMQConsumer") -> pika.BlockingConnection:
                tries, delay = self._max_retries, self._min_delay

                while True:
                    try:
                        return connection_property(consumer)
                    except self._reconnect_on:
                        tries = recalculate_tries(tries)

                        time.sleep(delay)

                        delay = recalculate_delay(delay)

            return wrapper

        return decorator

    def restart(self, resetter: Callback | None = None) -> Callable[[Callback], Callback]:
        def decorator(start_consuming_method: Callback) -> Callback:
            @functools.wraps(start_consuming_method)
            def wrapper(consumer: "RabbitMQConsumer") -> None:
                while True:
                    try:
                        if resetter is not None:
                            resetter(consumer)

                        start_consuming_method(consumer)
                    except ReconnectingError:
                        break
                    except Exception as error:
                        self._logger.info("Error %s occurred during consuming.", error)
                        continue

            return wrapper

        return decorator
