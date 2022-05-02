import asyncio
from sku_scraper import SkuScraper
from structlog.stdlib import get_logger

logger = get_logger().bind(deployment="sku-scraper")

sku_scraper = SkuScraper(logger)

async def main():
    await sku_scraper.process(urls=[
        "https://www.google.com/",
        "https://github.com/",
    ], marketplace="google_shopping")

asyncio.run(main())
