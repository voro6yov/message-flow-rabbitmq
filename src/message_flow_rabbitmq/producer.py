import logging
from typing import Any

import pika
from pika.adapters.blocking_connection import BlockingChannel

from .retry_manager import IRetryManager, RetryConfig, RetryManager

__all__ = ["RabbitMQProducer"]


class RabbitMQProducer:
    retry_config = RetryConfig()
    retry_manager: IRetryManager = RetryManager(retry_config)

    def __init__(self, dsn: str, id: str) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

        self._dsn = dsn
        self._id = id

        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    @property
    @retry_manager.reconnect()
    def connection(self) -> pika.BlockingConnection:
        if self._connection is None:
            self._connection = pika.BlockingConnection(pika.URLParameters(self._dsn))
        return self._connection

    @property
    def channel(self) -> BlockingChannel:
        if self._channel is None:
            self._channel = self.connection.channel()
        return self._channel

    def send(self, channel: str, body: bytes, headers: dict[str, Any] | None = None) -> None:
        self.channel.basic_publish(
            exchange=channel,
            routing_key="#",
            body=body,
            properties=pika.BasicProperties(
                headers=headers if headers is not None else {},
            ),
        )

    def close(self) -> None:
        self.channel.close()
        self.connection.close()
