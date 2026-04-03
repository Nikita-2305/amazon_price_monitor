import random
from proxy_fetcher import get_free_proxies

PROXY_LIST = get_free_proxies()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

class RotateUserAgentMiddleware:
    def process_request(self, request, spider):
        ua = random.choice(USER_AGENTS)
        request.headers["User-Agent"] = ua
        spider.logger.debug(f"Using UA: {ua[:50]}")

class ProxyMiddleware:
    def process_request(self, request, spider):
        if PROXY_LIST:
            proxy = random.choice(PROXY_LIST)
            request.meta["proxy"] = f"http://{proxy}"
            spider.logger.debug(f"Using proxy: {proxy}")