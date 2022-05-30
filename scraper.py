from aio_pika import IncomingMessage
from la_stopwatch import Stopwatch
from page_fetcher import Fetcher
from page_infra import Infra
from page_parser import Parser
from page_sku import SKU
from pydantic import AnyHttpUrl
from rabbit_models.sku_scraper import Body
from structlog.stdlib import BoundLogger


class Scraper:
    def __init__(
        self, redis_url: str, mongo_url: str, meilisearch_url: str, logger: BoundLogger
    ):
        self._logger = logger
        self._fetcher = Fetcher(logger=logger)
        self._parser = Parser(logger=logger)
        self._infra = Infra(
            redis_url=redis_url,
            mongo_url=mongo_url,
            meilisearch_url=meilisearch_url,
            logger=logger,
        )

    def on_finish(self, message: IncomingMessage, duration: int) -> None:
        body = Body.parse_raw(message.body)

        self._logger.info(
            event="Sku scraped",
            urls=body.urls,
            marketplace=body.marketplace,
            duration=str(duration),
        )

    @Stopwatch(callback=on_finish)
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
        body = Body.parse_raw(message.body)
        skus = []

        pages = await self._fetcher.fetch(
            urls=body.urls,
            marketplace=body.marketplace,
        )

        async for text, url in pages:
            items = self._parser.parse(text=text, url=url, marketplace=body.marketplace)

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
                        marketplace=body.marketplace,
                    )

        await self._infra.insert_skus(skus=skus, marketplace=body.marketplace)
        await message.ack()
