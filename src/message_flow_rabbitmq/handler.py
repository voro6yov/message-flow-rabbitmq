import logging
import multiprocessing as mp
from contextlib import contextmanager
from typing import Any, Callable, Generator

from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError
from pika.spec import Basic, BasicProperties

from .amqp_data import AMQPData
from .dead_letters import IDeadLetters

__all__ = ["Handler"]


mp.set_start_method("fork")


class Handler:
    def __init__(
        self,
        message_handler: Callable,
        dead_letters: IDeadLetters,
    ) -> None:
        self._logger = logging.getLogger(__name__)

        self._message_handler = message_handler
        self._dead_letters = dead_letters

    def __call__(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        properties: BasicProperties,
        body: bytes,
    ) -> None:
        amqp_data = AMQPData(channel, method, properties, body)

        try:
            self._handle_body(amqp_data)
        except AMQPConnectionError as error:
            self._logger.info("%s occurred.", error)
            raise

    def _handle_body(self, amqp_data: AMQPData) -> None:
        with self._handle_message(amqp_data.body, amqp_data.headers) as handler_process:
            while handler_process.is_alive():
                amqp_data.health_check()

        if handler_process.exitcode == 0:
            amqp_data.send_ack()
        else:
            amqp_data.send_nack(self._dead_letters.is_requeue_needed(amqp_data.headers))

    @contextmanager
    def _handle_message(self, body: bytes, headers: dict[str, Any]) -> Generator[mp.Process, None, None]:
        handler_process = mp.Process(target=self._message_handler, args=(body, headers))
        try:
            handler_process.start()
            yield handler_process
        except Exception as error:
            handler_process.terminate()
            self._logger.info("%s, process %s is terminated.", error, handler_process.ident)
            raise
        finally:
            handler_process.join()
