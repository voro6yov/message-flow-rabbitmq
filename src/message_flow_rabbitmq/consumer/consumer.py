import logging
from typing import Callable

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType

from ..retry_manager import RetryConfig
from ._consumer_construction import ConsumerMeta
from .dead_letters import DeadLetters, DeadLettersConfig
from .handler import Handler
from .subscription import Subscription

__all__ = ["RabbitMQConsumer"]


class RabbitMQConsumer(metaclass=ConsumerMeta):
    def __init__(
        self,
        dsn: str,
        id: str = "MessageFlowRabbitMQ",
        *,
        retry_config: RetryConfig = RetryConfig(),
        dead_letters_config: DeadLettersConfig = DeadLettersConfig(),
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self._dsn = dsn
        self._id = id

        self._retry_config = retry_config
        self._dead_letters = DeadLetters(dead_letters_config)

        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

        self._subscriptions: list[Subscription] = []

    def get_connection(self) -> pika.BlockingConnection:
        if self._connection is None:
            self._connection = pika.BlockingConnection(pika.URLParameters(self._dsn))

        return self._connection

    def get_channel(self) -> BlockingChannel:
        if self._channel is None:
            self._channel = self.get_connection().channel()

        return self._channel

    def subscribe(self, channels: set[str], handler: Callable[[bytes, dict[str, str]], None]) -> None:
        self._subscriptions.append(Subscription(channels, handler))

    def reset(self) -> None:
        if self._channel is not None and self._channel.is_closed:
            self._channel = None

        if self._connection is not None and self._connection.is_closed:
            self._connection = None

    def start_consuming(self) -> None:
        self._setup_subscriptions()
        self._logger.info("Starting to consume messages.")
        self.get_channel().start_consuming()

    def close(self) -> None:
        self.get_channel().close()
        self.get_connection().close()

    def _declare_exchange(self, exchange_name: str) -> None:
        self.get_channel().exchange_declare(exchange=exchange_name, exchange_type=ExchangeType.topic, durable=True)

    def _declare_queue(self, channel: str) -> None:
        self.get_channel().basic_qos(prefetch_count=1)
        self.get_channel().queue_declare(
            queue=f"{channel}.{self._id}",
            durable=True,
            arguments=self._dead_letters.make_arguments(self.get_channel(), f"{channel}.{self._id}"),
        )

    def _bind_topic_to_queue(self, channel: str) -> None:
        self.get_channel().queue_bind(exchange=channel, queue=f"{channel}.{self._id}", routing_key="#")

    def _bind_handler_to_queue(self, channel: str, handler: Callable[[bytes, dict[str, str]], None]) -> None:
        wrapped_callback = Handler(handler, self._dead_letters)
        self.get_channel().basic_consume(queue=f"{channel}.{self._id}", on_message_callback=wrapped_callback)

    def _setup_subscriptions(self) -> None:
        for subscription in self._subscriptions:
            for channel in subscription.channels:
                self._declare_exchange(channel)
                self._declare_queue(channel)
                self._bind_topic_to_queue(channel)
                self._bind_handler_to_queue(channel, subscription.handler)
