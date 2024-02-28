from dataclasses import dataclass
from typing import Any

from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

__all__ = ["AMQPData"]


@dataclass
class AMQPData:
    channel: BlockingChannel
    method: Basic.Deliver
    properties: BasicProperties
    body: bytes

    @property
    def exchange(self) -> str:
        return self.method.exchange

    @property
    def routing_key(self) -> str:
        return self.method.routing_key

    @property
    def delivery_tag(self) -> int:
        return self.method.delivery_tag

    @property
    def headers(self) -> dict[str, Any]:
        return self.properties.headers

    def send_ack(self) -> None:
        self.channel.basic_ack(delivery_tag=self.delivery_tag)

    def send_nack(self, requeue: bool = True) -> None:
        self.channel.basic_nack(delivery_tag=self.delivery_tag, requeue=requeue)

    def health_check(self) -> None:
        self.channel.connection.process_data_events()
