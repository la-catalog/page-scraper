from page_fetcher import Fetcher
from la_stopwatch import Stopwatch
from structlog.stdlib import BoundLogger


class SkuScraper:
    def __init__(self, logger: BoundLogger):
        self._logger = logger
        self._fetcher = Fetcher(logger=logger)

    async def process(self, urls: list[str], marketplace: str) -> None:
        stopwatch = Stopwatch()
        fetch_coroutine = await self._fetcher.fetch(urls=urls, marketplace=marketplace)

        async for text in fetch_coroutine:
            print(text[:10])

            # TODO: when parser yield str, means that you should scrape the url
            while (response := None):
                text = await fetch_coroutine.asend("https://twitter.com/")
                print(text[:10])

        self._logger.info(
            "Sku scraped", marketplace=marketplace, duration=str(stopwatch)
        )
