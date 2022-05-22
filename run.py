import asyncio

from structlog.stdlib import get_logger

from sku_scraper import SkuScraper

logger = get_logger().bind(deployment="sku-scraper")

sku_scraper = SkuScraper(logger)


async def main():
    await sku_scraper.process(
        urls=[
            "https://www.rihappy.com.br/dino-papa-tudo-elka/p",
            # "https://www.rihappy.com.br/dino-papa-tudo-elka/p",
        ],
        marketplace="rihappy",
    )


asyncio.run(main())
