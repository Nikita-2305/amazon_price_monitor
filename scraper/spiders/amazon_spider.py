import scrapy
from scrapy_playwright.page import PageMethod
from datetime import datetime
from urllib.parse import quote_plus
import os

KA_PINCODES = ["560001", "570001", "580020", "580001", "590001"]
SKF_MODELS = ["6205", "6206"]

class AmazonBearingSpider(scrapy.Spider):
    name = "amazon_bearing"
    allowed_domains = ["amazon.in"]

    def start_requests(self):
        for model in SKF_MODELS:
            query = f"SKF bearing {model}"
            url = f"https://www.amazon.in/s?k={quote_plus(query)}"
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={
                    "model": model,
                    "pincode": KA_PINCODES[0],
                    "page": 1,
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "viewport": {"width": 1280, "height": 800},
                        "locale": "en-IN",
                        "timezone_id": "Asia/Kolkata",
                    },
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", 4000),
                    ],
                },
                errback=self.handle_error,
            )

    async def parse_search_results(self, response):
        model = response.meta["model"]
        pincode = response.meta["pincode"]
        page = response.meta["page"]
        playwright_page = response.meta.get("playwright_page")

        self.logger.info(f"Parsing search: SKF {model} | Page {page}")

        # ✅ KEY FIX: Get fresh HTML directly from Playwright page
        if playwright_page:
            try:
                # Wait for products to appear
                await playwright_page.wait_for_selector(
                    "div[data-component-type='s-search-result']",
                    timeout=20000
                )
                # Scroll to load lazy content
                await playwright_page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await playwright_page.wait_for_timeout(2000)
                await playwright_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await playwright_page.wait_for_timeout(2000)

                # Get the fully rendered HTML
                content = await playwright_page.content()
                await playwright_page.close()

                # Replace scrapy response with fresh playwright content
                from scrapy.http import HtmlResponse
                response = HtmlResponse(
                    url=response.url,
                    body=content,
                    encoding="utf-8",
                    request=response.request,
                )
                self.logger.info("✅ Got fresh HTML from Playwright page")
            except Exception as e:
                self.logger.error(f"Playwright page error: {e}")
                if not playwright_page.is_closed():
                    await playwright_page.close()

        # Save debug HTML
        os.makedirs("logs", exist_ok=True)
        with open(f"logs/debug_search_{model}_p{page}.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        if "captcha" in response.text.lower() or "Enter the characters" in response.text:
            self.logger.warning(f"CAPTCHA detected for {model}")
            return

        products = response.css("div[data-asin][data-component-type='s-search-result']")
        self.logger.info(f"🔥 Found {len(products)} products for SKF {model}")

        if len(products) == 0:
            self.logger.warning("No products — check debug HTML")
            return

        for product in products:
            asin = product.attrib.get("data-asin", "").strip()
            if not asin or len(asin) < 5:
                continue

            title = (
                product.css("h2 span::text").get("")
                or product.css("h2 a span::text").get("")
            ).strip()

            price_whole = (
                product.css("span.a-price-whole::text").get("0")
                .strip().replace(",", "").replace(".", "")
            )
            price_frac = product.css("span.a-price-fraction::text").get("00").strip()
            mrp_raw = (
                product.css("span.a-text-price span.a-offscreen::text").get("")
                .replace("₹", "").replace(",", "").strip()
            )

            try:
                price = float(f"{price_whole}.{price_frac}")
            except Exception:
                price = 0.0

            self.logger.info(f"  → ASIN:{asin} | {title[:40]} | ₹{price}")

            if price > 0:
                yield scrapy.Request(
                    url=f"https://www.amazon.in/dp/{asin}",
                    callback=self.parse_product_page,
                    meta={
                        "asin": asin,
                        "title": title,
                        "model": model,
                        "search_price": price,
                        "mrp": mrp_raw,
                        "pincode": pincode,
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context_kwargs": {
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            "viewport": {"width": 1280, "height": 800},
                            "locale": "en-IN",
                            "timezone_id": "Asia/Kolkata",
                        },
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "domcontentloaded"),
                            PageMethod("wait_for_timeout", 3000),
                        ],
                    },
                    errback=self.handle_error,
                )

        if page < 2:
            next_url = f"https://www.amazon.in/s?k={quote_plus(f'SKF bearing {model}')}&page={page+1}"
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={
                    "model": model,
                    "pincode": pincode,
                    "page": page + 1,
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        "viewport": {"width": 1280, "height": 800},
                        "locale": "en-IN",
                        "timezone_id": "Asia/Kolkata",
                    },
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", 4000),
                    ],
                },
                errback=self.handle_error,
            )

    async def parse_product_page(self, response):
        asin = response.meta["asin"]
        title = response.meta.get("title", "")
        model = response.meta["model"]
        mrp = response.meta["mrp"]
        pincode = response.meta["pincode"]
        playwright_page = response.meta.get("playwright_page")

        self.logger.info(f"Product page: {asin}")

        # Get fresh HTML from Playwright
        if playwright_page:
            try:
                await playwright_page.wait_for_selector("#productTitle", timeout=15000)
                await playwright_page.wait_for_timeout(2000)
                content = await playwright_page.content()
                await playwright_page.close()

                from scrapy.http import HtmlResponse
                response = HtmlResponse(
                    url=response.url,
                    body=content,
                    encoding="utf-8",
                    request=response.request,
                )
            except Exception as e:
                self.logger.error(f"Product page error: {e}")
                if not playwright_page.is_closed():
                    await playwright_page.close()

        if "captcha" in response.text.lower():
            self.logger.warning(f"CAPTCHA on product {asin}")
            return

        if not title:
            title = response.css("#productTitle::text").get("").strip()

        buy_box_seller = (
            response.css("#sellerProfileTriggerId::text").get("").strip()
            or response.css("#merchant-info a::text").get("").strip()
            or response.css("#tabular-buybox-truncate-0 .a-truncate-full::text").get("").strip()
            or response.css(".tabular-buybox-text span::text").get("").strip()
            or "Unknown"
        )

        price_whole = (
            response.css("#corePrice_feature_div span.a-price-whole::text")
            .get("0").replace(",", "").replace(".", "").strip()
        )
        price_frac = (
            response.css("#corePrice_feature_div span.a-price-fraction::text")
            .get("00").strip()
        )

        try:
            price = float(f"{price_whole}.{price_frac}")
        except Exception:
            price = response.meta.get("search_price", 0.0)

        fulfillment = response.css("#merchant-info::text").getall()
        fba = "FBA" if any("Amazon" in t for t in fulfillment) else "FBM"
        availability = response.css("#availability span::text").get("Unknown").strip()

        if price > 0:
            yield {
                "asin": asin,
                "product_title": title[:200],
                "model": model,
                "seller_name": buy_box_seller,
                "price": price,
                "mrp": mrp,
                "is_buy_box_winner": True,
                "fba_status": fba,
                "availability": availability,
                "pincode": pincode,
                "scraped_at": datetime.now().isoformat(),
            }

        yield scrapy.Request(
            url=f"https://www.amazon.in/gp/offer-listing/{asin}/",
            callback=self.parse_all_sellers,
            meta={
                "asin": asin,
                "title": title,
                "model": model,
                "mrp": mrp,
                "pincode": pincode,
                "buy_box_seller": buy_box_seller,
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "viewport": {"width": 1280, "height": 800},
                    "locale": "en-IN",
                    "timezone_id": "Asia/Kolkata",
                },
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod("wait_for_timeout", 2000),
                ],
            },
            errback=self.handle_error,
        )

    async def parse_all_sellers(self, response):
        asin = response.meta["asin"]
        title = response.meta["title"]
        model = response.meta["model"]
        mrp = response.meta["mrp"]
        pincode = response.meta["pincode"]
        buy_box_seller = response.meta["buy_box_seller"]
        playwright_page = response.meta.get("playwright_page")

        if playwright_page:
            try:
                await playwright_page.close()
            except Exception:
                pass

        offers = response.css("#olpOfferList .olp-offering-row")
        self.logger.info(f"{len(offers)} offers for {asin}")

        for offer in offers:
            seller = (
                offer.css(".olp-seller-name a::text").get("").strip()
                or offer.css("h3.a-size-small::text").get("").strip()
                or "Amazon.in"
            )
            price_raw = (
                offer.css(".olp-offer-price::text").get("0")
                .replace("₹", "").replace(",", "").strip()
            )
            try:
                price = float(price_raw)
            except Exception:
                price = 0.0

            if seller and price > 0:
                yield {
                    "asin": asin,
                    "product_title": title[:200],
                    "model": model,
                    "seller_name": seller,
                    "price": price,
                    "mrp": mrp,
                    "is_buy_box_winner": seller == buy_box_seller,
                    "fba_status": "FBA",
                    "availability": "In Stock",
                    "pincode": pincode,
                    "scraped_at": datetime.now().isoformat(),
                }

    def handle_error(self, failure):
        self.logger.error(
            f"Failed: {failure.request.url} — {str(failure.value)}"
        )