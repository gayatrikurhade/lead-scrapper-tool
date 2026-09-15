BOT_NAME = "lead_scraper"

SPIDER_MODULES = ["lead_scraper.spiders"]
NEWSPIDER_MODULE = "lead_scraper.spiders"

ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 8

DOWNLOAD_TIMEOUT = 15

RETRY_ENABLED = True
RETRY_TIMES = 2

COOKIES_ENABLED = False

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)
LOG_LEVEL = "INFO"