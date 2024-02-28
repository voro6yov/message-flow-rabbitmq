import logging
from random import randint
from uuid import uuid4

import click

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@click.command()
def consume():
    from message_flow_rabbitmq import RabbitMQConsumer

    def handler(*args, **kwargs):
        logger.info("args: %s, kwargs: %s", args, kwargs)
        if randint(0, 1):
            raise Exception

        # time.sleep(10 * 3)

    consumer = RabbitMQConsumer("amqp://localhost:5672/?heartbeat=10", id="test")
    consumer.subscribe({"qfq", "sqs"}, handler)
    try:
        consumer.start_consuming()
    except KeyboardInterrupt:
        consumer.close()


@click.command()
def produce():
    from message_flow_rabbitmq import RabbitMQProducer

    producer = RabbitMQProducer("amqp://localhost:5672/", "test")

    producer.send("sqs", b"Hello World!", headers={"ID": uuid4().hex})
    producer.close()


cli.add_command(consume)
cli.add_command(produce)


if __name__ == "__main__":
    cli()
