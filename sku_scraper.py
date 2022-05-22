from la_stopwatch import Stopwatch
from page_fetcher import Fetcher
from page_parser import Parser
from page_sku import SKU
from pydantic import AnyHttpUrl
from structlog.stdlib import BoundLogger


class SkuScraper:
    def __init__(self, logger: BoundLogger):
        self._logger = logger
        self._fetcher = Fetcher(logger=logger)
        self._parser = Parser(logger=logger)

    def on_scrap(self, urls: list[str], marketplace: str, duration: int):
        self._logger.info(
            event="Sku scraped",
            urls=urls,
            marketplace=marketplace,
            duration=str(duration),
        )

    @Stopwatch(callback=on_scrap)
    async def process(self, urls: list[str], marketplace: str) -> None:
        skus = []
        fetch_co = await self._fetcher.fetch(urls=urls, marketplace=marketplace)

        async for text, url in fetch_co:
            parse_gen = self._parser.parse(text=text, url=url, marketplace=marketplace)

            for item in parse_gen:
                while item:
                    if isinstance(item, SKU):
                        skus.append(item)
                        break
                    elif isinstance(item, AnyHttpUrl):
                        text, url = await fetch_co.asend(item)
                        item = parse_gen.send((text, url))
                    else:
                        self._logger.warning(
                            event="Item ignored",
                            urls=urls,
                            marketplace=marketplace,
                        )
                        break
