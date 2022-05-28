import asyncio

from aio_pika import Connection, connect
from structlog.stdlib import get_logger

from scraper import Scraper

logger = get_logger().bind(deployment="sku-scraper")

scraper = Scraper(logger)


async def consume_queue(connection: Connection, queue_name: str):
    channel = await connection.channel()

    async with channel:
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(name=queue_name, durable=True)

        await queue.consume(callback=scraper.on_message)
        await asyncio.Future()


async def main():
    connection = await connect("amqp://username:password@127.0.0.1:5672")

    async with connection:
        await asyncio.gather(
            consume_queue(connection, "amazon_sku"),
            consume_queue(connection, "americanas_sku"),
            consume_queue(connection, "rihappy_sku"),
        )


asyncio.run(main())
