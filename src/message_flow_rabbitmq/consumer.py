import logging
from typing import Any
from uuid import uuid4

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType

from .dead_letters import DeadLetters, DeadLettersConfig, IDeadLetters
from .handler import Handler
from .retry_manager import IRetryManager, RetryConfig, RetryManager
from .subscription import Subscription

__all__ = ["RabbitMQConsumer"]


class RabbitMQConsumer:
    retry_config = RetryConfig()
    retry_manager: IRetryManager = RetryManager(retry_config)

    def __init__(
        self,
        dsn: str,
        id: str | None = None,
        dead_letters: IDeadLetters = DeadLetters(DeadLettersConfig()),
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self._id = id or uuid4().hex
        self._dsn = dsn
        self._dead_letters = dead_letters

        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

        self._subscriptions: list[Subscription] = []

    @property
    @retry_manager.reconnect()
    def connection(self) -> pika.BlockingConnection:
        if self._connection is None:
            self._connection = pika.BlockingConnection(pika.ConnectionParameters(self._dsn))

        return self._connection

    @property
    def channel(self) -> BlockingChannel:
        if self._channel is None:
            self._channel = self.connection.channel()

        return self._channel

    def subscribe(self, channels: set[str], handler: Any) -> None:
        self._subscriptions.append(Subscription(channels, handler))

    def reset(self) -> None:
        if self._channel is not None and self._channel.is_closed:
            self._channel = None

        if self._connection is not None and self._connection.is_closed:
            self._connection = None

    @retry_manager.restart(reset)
    def start_consuming(self) -> None:
        self._setup_subscriptions()
        self._logger.info("Starting to consume messages.")
        self.channel.start_consuming()

    def close(self) -> None:
        self.channel.close()
        self.connection.close()

    def _declare_exchange(self, exchange_name: str) -> None:
        self.channel.exchange_declare(exchange=exchange_name, exchange_type=ExchangeType.topic, durable=True)

    def _declare_queue(self, channel: str) -> None:
        self.channel.basic_qos(prefetch_count=1)
        self.channel.queue_declare(
            queue=f"{channel}.{self._id}",
            durable=True,
            arguments=self._dead_letters.make_arguments(self.channel, f"{channel}.{self._id}"),
        )

    def _bind_topic_to_queue(self, channel: str) -> None:
        self.channel.queue_bind(exchange=channel, queue=f"{channel}.{self._id}", routing_key="#")

    def _bind_handler_to_queue(self, channel: str, handler: Any) -> None:
        wrapped_callback = Handler(handler, self._dead_letters)
        self.channel.basic_consume(queue=f"{channel}.{self._id}", on_message_callback=wrapped_callback)

    def _setup_subscriptions(self) -> None:
        for subscription in self._subscriptions:
            for channel in subscription.channels:
                self._declare_exchange(channel)
                self._declare_queue(channel)
                self._bind_topic_to_queue(channel)
                self._bind_handler_to_queue(channel, subscription.handler)
