from abc import ABCMeta
from typing import TYPE_CHECKING

from ..retry_manager import RetryManager

if TYPE_CHECKING:
    from .producer import RabbitMQProducer

__all__ = ["ProducerMeta"]


class ProducerMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls: type["RabbitMQProducer"] = super().__new__(mcs, name, bases, namespace, **kwargs)

        def decorated_init(producer_constructor):
            def wrapper(self, *args, **kwargs):
                producer_constructor(self, *args, **kwargs)
                mcs.add_retries(self)

            return wrapper

        cls.__init__ = decorated_init(cls.__init__)

        return cls

    @staticmethod
    def add_retries(producer: "RabbitMQProducer") -> None:
        retry_manager = RetryManager(producer._retry_config)
        cls = producer.__class__

        cls.get_connection = retry_manager.reconnect()(cls.get_connection)  # type: ignore
