import asyncio
import os

from aio_pika import Connection, connect
from page_infra.options import get_marketplace_infra
from structlog.stdlib import get_logger

from scraper import Scraper

logger = get_logger().bind(deployment="sku-scraper")

scraper = Scraper(
    redis_url=os.environ["REDIS_URL"],
    mongo_url=os.environ["MONGO_URL"],
    meilisearch_url=os.environ["MEILI_URL"],
    meilisearch_key=os.environ["MEILI_KEY"],
    logger=logger,
)


async def consume_queue(connection: Connection, marketplace: str):
    infra = get_marketplace_infra(marketplace=marketplace, logger=logger)
    channel = await connection.channel()

    async with channel:
        await channel.set_qos(prefetch_count=1)

        queue = await channel.declare_queue(
            name=infra.sku_queue,
            durable=True,
            arguments={"x-max-priority": 10, "x-queue-mode": "lazy"},
        )

        await queue.consume(callback=scraper.on_message)
        await asyncio.Future()


async def main():
    await scraper.setup()

    connection = await connect(os.environ["RABBIT_URL"])

    async with connection:
        await asyncio.gather(
            consume_queue(connection, "mercado_livre"),
            consume_queue(connection, "rihappy"),
        )


asyncio.run(main())
