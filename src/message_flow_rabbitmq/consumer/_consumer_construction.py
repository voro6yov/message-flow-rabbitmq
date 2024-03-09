from abc import ABCMeta
from typing import TYPE_CHECKING

from ..retry_manager import RetryManager

if TYPE_CHECKING:
    from .consumer import RabbitMQConsumer

__all__ = ["ConsumerMeta"]


class ConsumerMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        cls: type["RabbitMQConsumer"] = super().__new__(mcs, name, bases, namespace, **kwargs)

        def decorated_init(consumer_constructor):
            def wrapper(self, *args, **kwargs):
                consumer_constructor(self, *args, **kwargs)
                mcs.add_retries(self)

            return wrapper

        cls.__init__ = decorated_init(cls.__init__)

        return cls

    @staticmethod
    def add_retries(consumer: "RabbitMQConsumer") -> None:
        retry_manager = RetryManager(consumer._retry_config)
        cls = consumer.__class__

        cls.get_connection = retry_manager.reconnect()(cls.get_connection)  # type: ignore
        cls.start_consuming = retry_manager.restart(cls.reset)(cls.start_consuming)  # type: ignore
