BOT_NAME = "amazon_price_monitor"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 60

CONCURRENT_REQUESTS = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 1

AUTOTHROTTLE_ENABLED = False
RETRY_ENABLED = True
RETRY_TIMES = 2

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000

DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.RotateUserAgentMiddleware": 400,
}

# Both CSV and PostgreSQL pipelines active
ITEM_PIPELINES = {
    "scraper.pipelines.CSVPipeline": 300,
    "scraper.pipelines.PostgreSQLPipeline": 400,
}

LOG_LEVEL = "INFO"
LOG_FILE = "logs/scraper.log"
TELNETCONSOLE_ENABLED = False