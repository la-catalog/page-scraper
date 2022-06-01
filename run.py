import asyncio
import os

from aio_pika import Connection, connect
from structlog.stdlib import get_logger

from scraper import Scraper

logger = get_logger().bind(deployment="sku-scraper")

scraper = Scraper(
    redis_url=os.environ["REDIS_URL"],
    mongo_url=os.environ["MONGO_URL"],
    meilisearch_url=os.environ["MEILISEARCH_URL"],
    logger=logger,
)


async def consume_queue(connection: Connection, queue_name: str):
    channel = await connection.channel()

    async with channel:
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(name=queue_name, durable=True)

        await queue.consume(callback=scraper.on_message)
        await asyncio.Future()


async def main():
    await scraper.setup()

    connection = await connect(os.environ["RABBIT_URL"])

    async with connection:
        await asyncio.gather(
            consume_queue(connection, "mercado_livre_sku"),
            consume_queue(connection, "rihappy_sku"),
        )


asyncio.run(main())
