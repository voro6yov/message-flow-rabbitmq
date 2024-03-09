import logging

import pika
from pika.adapters.blocking_connection import BlockingChannel

from ..retry_manager import RetryConfig
from ._producer_construction import ProducerMeta

__all__ = ["RabbitMQProducer"]


class RabbitMQProducer(metaclass=ProducerMeta):
    def __init__(
        self,
        dsn: str,
        id: str = "MessageFlowRabbitMQ",
        *,
        retry_config: RetryConfig = RetryConfig(),
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self._dsn = dsn
        self._id = id

        self._retry_config = retry_config

        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def get_connection(self) -> pika.BlockingConnection:
        if self._connection is None:
            self._connection = pika.BlockingConnection(pika.URLParameters(self._dsn))
        return self._connection

    def get_channel(self) -> BlockingChannel:
        if self._channel is None:
            self._channel = self.get_connection().channel()
        return self._channel

    def send(self, channel: str, body: bytes, headers: dict[str, str] | None = None) -> None:
        self.get_channel().basic_publish(
            exchange=channel,
            routing_key="#",
            body=body,
            properties=pika.BasicProperties(
                headers=headers if headers is not None else {},
            ),
        )

    def close(self) -> None:
        self.get_channel().close()
        self.get_connection().close()
