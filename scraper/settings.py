BOT_NAME = "amazon_price_monitor"

SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

ROBOTSTXT_OBEY = False

DOWNLOAD_DELAY = 8
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 120

CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

AUTOTHROTTLE_ENABLED = False
RETRY_ENABLED = True
RETRY_TIMES = 3

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "slow_mo": 100,        # ← slows actions so page loads properly
    "args": [
        "--no-sandbox",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ],
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 2

DOWNLOADER_MIDDLEWARES = {
    "scraper.middlewares.RotateUserAgentMiddleware": 400,
}

ITEM_PIPELINES = {
    "scraper.pipelines.CSVPipeline": 300,
    "scraper.pipelines.PostgreSQLPipeline": 400,
}

LOG_LEVEL = "DEBUG"
LOG_FILE = "logs/scraper.log"
TELNETCONSOLE_ENABLED = False