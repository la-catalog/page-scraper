from aio_pika import IncomingMessage
from la_stopwatch import Stopwatch
from page_fetcher import Fetcher
from page_parser import Parser
from page_sku import SKU
from pydantic import AnyHttpUrl
from rabbit_models.sku_scraper import Body
from structlog.stdlib import BoundLogger


class Scraper:
    def __init__(self, logger: BoundLogger):
        self._logger = logger
        self._fetcher = Fetcher(logger=logger)
        self._parser = Parser(logger=logger)

    def on_finish(self, message: IncomingMessage, duration: int):
        content = Body.parse_raw(message.body)

        self._logger.info(
            event="Sku scraped",
            urls=content.urls,
            marketplace=content.marketplace,
            duration=str(duration),
        )

    @Stopwatch(callback=on_finish)
    async def on_message(self, message: IncomingMessage) -> None:
        content = Body.parse_raw(message.body)
        skus = []

        pages = await self._fetcher.fetch(
            urls=content.urls,
            marketplace=content.marketplace,
        )

        async for text, url in pages:
            items = self._parser.parse(
                text=text, url=url, marketplace=content.marketplace
            )

            for item in items:
                while item:
                    if isinstance(item, SKU):
                        skus.append(item)
                        break
                    elif isinstance(item, AnyHttpUrl):
                        text, url = await pages.asend(item)
                        item = items.send((text, url))
                    else:
                        self._logger.warning(
                            event="Item ignored",
                            item=str(item),
                            url=url,
                            marketplace=content.marketplace,
                        )
                        break

        await message.ack()

    async def scrape(self, urls: list[str], marketplace: str) -> None:
        """ """

        pages = await self._fetcher.fetch(
            urls=urls,
            marketplace=marketplace,
        )

        async for text, url in pages:
            items = self._parser.parse(text=text, url=url, marketplace=marketplace)

            for item in items:
                while item:
                    if isinstance(item, SKU):
                        yield item
                        break

                    if isinstance(item, AnyHttpUrl):
                        text, url = await pages.asend(item)
                        item = items.send((text, url))
                        continue

                    self._logger.warning(
                        event="Item ignored",
                        item=str(item),
                        url=url,
                        marketplace=marketplace,
                    )
                    break
