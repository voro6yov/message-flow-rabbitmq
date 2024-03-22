import logging

from pika.adapters.blocking_connection import BlockingChannel
from pika.exchange_type import ExchangeType

from .dead_letters_config import DeadLettersConfig

__all__ = ["DeadLetters"]


class DeadLetters:
    ID: str = "RabbitMQMessageID"

    def __init__(
        self,
        config: DeadLettersConfig,
    ) -> None:
        self._exchange_name: str = config.get("exchange_name", "dead-letters")
        self._routing_key: str = config.get("routing_key", "dlx-routing-key")

        self._max_requeue_counter: int = config.get("max_requeue_counter", 3)

        self._counters: dict[str, int] = {}

        self._logger = logging.getLogger(__name__)

    def is_requeue_needed(self, headers: dict[str, str]) -> bool:
        message_id = self._get_message_id(headers)

        self._increment_counter(message_id)

        requeue = self._counters[message_id] < self._max_requeue_counter

        if not requeue:
            self._logger.info("Message %s will be sent to DLX.", message_id)
            del self._counters[message_id]

        return requeue

    def make_arguments(self, channel: BlockingChannel, queue_name: str) -> dict[str, str]:
        return self._dead_letters_exchange_declare(channel, queue_name)

    def _get_message_id(self, headers: dict[str, str]) -> str:
        if (message_id := headers.get(self.ID)) is None:
            raise RuntimeError("Message ID is not provided.")

        return message_id

    def _increment_counter(self, message_id: str) -> None:
        self._initialize_counter(message_id)

        self._counters[message_id] += 1

    def _initialize_counter(self, message_id: str) -> None:
        if self._counters.get(message_id) is None:
            self._counters[message_id] = 0

    def _dead_letters_exchange_declare(self, channel: BlockingChannel, queue_name: str) -> dict[str, str]:
        channel.exchange_declare(
            exchange=self._exchange_name,
            exchange_type=ExchangeType.topic,
        )

        dlx_queue_name = f"{queue_name}-dlx"
        dlx_routing_key = f"{self._routing_key}-{queue_name}"

        self._deal_letters_exchange_queue_declare(channel, dlx_queue_name)
        channel.queue_bind(exchange=self._exchange_name, queue=dlx_queue_name, routing_key=dlx_routing_key)

        return {
            "x-dead-letter-exchange": self._exchange_name,
            "x-dead-letter-routing-key": dlx_routing_key,
        }

    def _deal_letters_exchange_queue_declare(self, channel: BlockingChannel, dlx_queue_name: str) -> None:
        channel.queue_declare(
            queue=dlx_queue_name,
            durable=True,
            arguments={
                "x-queue-mode": "lazy",
            },
        )
