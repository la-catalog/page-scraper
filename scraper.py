from aio_pika import IncomingMessage
from la_stopwatch import Stopwatch
from page_fetcher import Fetcher
from page_infra import Infra
from page_models import SKU
from page_parser import Parser
from pydantic import AnyHttpUrl
from rabbit_models.page_scraper import Body
from structlog.stdlib import BoundLogger


class Scraper:
    def __init__(
        self,
        redis_url: str,
        mongo_url: str,
        meilisearch_url: str,
        meilisearch_key: str,
        logger: BoundLogger,
    ):
        self._logger = logger
        self._fetcher = Fetcher(logger=logger)
        self._parser = Parser(logger=logger)
        self._infra = Infra(
            redis_url=redis_url,
            mongo_url=mongo_url,
            meilisearch_url=meilisearch_url,
            meilisearch_key=meilisearch_key,
            logger=logger,
        )

    async def setup(self):
        await self._infra.setup_sku_database()
        await self._infra.setup_catalog_database()

    async def on_message(self, message: IncomingMessage) -> None:
        """
        Scrape URLs and send their SKUs to database.

        This function is a little complicated because:
            1 - fetcher is a coroutine that can receive
                a url at any time and return it content
            2 - parser is a generator that can receive
                a content at any time and return an item
            3 - There is a *while* loop that utilizes
                both mechanics so at any time the parser can
                pass a URL for the fetcher and get it content
        """
        stopwatch = Stopwatch()
        body = Body.parse_raw(message.body)
        marketplace = body.marketplace
        urls = body.urls
        skus = []

        urls = await self._infra.discard_recent_urls(
            urls=urls,
            marketplace=marketplace,
        )

        urls = await self._infra.identify_new_urls(
            urls=urls,
            marketplace=marketplace,
        )

        pages = await self._fetcher.fetch(
            urls=urls,
            marketplace=marketplace,
        )

        async for text, url in pages:
            items = self._parser.parse(text=text, url=url, marketplace=marketplace)

            for item in items:
                while isinstance(item, AnyHttpUrl):
                    text, url = await pages.asend(item)
                    item = items.send((text, url))

                if isinstance(item, SKU):
                    skus.append(item)
                else:
                    self._logger.warning(
                        event="Item ignored",
                        item=str(item),
                        url=url,
                        marketplace=marketplace,
                    )

        skus = await self._infra.identify_new_skus(skus=skus, marketplace=marketplace)

        await self._infra.insert_skus(skus=skus, marketplace=marketplace)
        await message.ack()

        self._logger.info(
            event="Message processed",
            urls=urls,
            marketplace=marketplace,
            duration=str(stopwatch),
        )
