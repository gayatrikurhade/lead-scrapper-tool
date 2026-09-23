import scrapy
import time
from urllib.parse import urljoin, urlparse

CONTACT_KEYWORDS = [
    "contact",
    "contact-us",
    "contactus",
    "get-in-touch",
    "reach-us",
]

IMPORTANT_KEYWORDS = [
    "about",
    "about-us",
    "aboutus",
    "company",
    "who-we-are",
    "team",
    "our-team",
    "our-people",
    "leadership",
    "management",
    "director",
    "directors",
    "board",
    "profile",
]

class WebsiteSpider(scrapy.Spider):
    name = "website_spider"
    custom_settings = {
        "DEPTH_LIMIT": 2,
    }

    def __init__(
        self,
        start_url=None,
        max_pages=5,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.start_url = start_url

        try:
            self.max_pages = int(max_pages)
        except (ValueError, TypeError):
            self.max_pages = 5

        self.visited = set()
        self.pages_crawled = 0

    async def start(self):

        if not self.start_url:
            self.logger.error(
                "[SCRAPY ERROR] start_url is empty"
            )
            return

        self.logger.info(
            f"[SCRAPY] Starting URL: {self.start_url}"
        )
    
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse,
            errback=self.handle_error,
            priority=1000
        )

    def parse(self, response):

        page_start = time.perf_counter()

        content_type = response.headers.get(
            b"Content-type",
            b""
        ).decode(
            "utf-8",
            errors="ignore"
        ).lower()

        if "text/html" not in content_type:
            print(
                f"[SCRAPY] Skipping non-HTML response: "
                f"{response.url} | {content_type}"
            )
            return

        if self.pages_crawled >= self.max_pages:
            return
        current_url = (
            response.url
            .split("#")[0]
            .rstrip("/")
        )

        if current_url in self.visited:
            return

        self.visited.add(current_url)

        self.pages_crawled += 1

        print(
            f"[SCRAPY] Saved page "
            f"{self.pages_crawled}/{self.max_pages}: "
            f"{current_url}"
        )

        yield {
            "url": current_url,
            "raw_html": response.text
        }

        page_time = time.perf_counter() - page_start

        print(
            f"[SCRAPY TIME] Page "
            f"{self.pages_crawled}/{self.max_pages} "
            f"{current_url} = "
            f"{page_time:.2f} seconds"
        )

        if self.pages_crawled >= self.max_pages:
            return

        links = []

        for link_element in response.css("a"):

            href = link_element.attrib.get("href")

            if not href:
                continue

            href = href.strip()

            if href.startswith(
                (
                    "mailto:",
                    "tel:",
                    "javascript:",
                    "#"
                )):
                continue

            full_url = urljoin(
                response.url,
                href
            )

            full_url = (
                full_url
                .split("#")[0]
                .rstrip("/")
            )
            if "add-to-cart=" in full_url.lower():
                continue

            skip_keywords = [
                "/my-account",
                "/cart",
                "/checkout",
                "/wishlist",
            ]

            if any(
                keyword in full_url.lower()
                for keyword in skip_keywords
            ):
                continue

            if not self.is_same_domain(
                self.start_url,
                full_url
            ):
                continue

            if full_url in self.visited:
                continue

            link_text = " ".join(
                link_element.css(
                    "::text"
                ).getall()
            ).strip()

            combined_text = (
                f"{full_url} {link_text}"
            ).lower()

            links.append(
                {
                    "url": full_url,
                    "text": combined_text
                }
            )

        for link_data in links:

            if self.pages_crawled >= self.max_pages:
                break

            link = link_data["url"]
            link_text = link_data["text"]

            priority = self.get_link_priority(
                link,
                link_text
            )

            if priority >= 100:
                priority_name = "CONTACT"

            elif priority >= 80:
                priority_name = "IMPORTANT"

            else:
                priority_name = "NORMAL"

            print(
                f"[SCRAPY] Queued "
                f"{priority_name} page: "
                f"{link} "
                f"(priority={priority})"
            )

            yield scrapy.Request(
                url=link,
                callback=self.parse,
                errback=self.handle_error,
                priority=priority
            )

    def get_link_priority(
        self,
        url,
        link_text=""
    ):
        """
        Assign priority to URLs.

        Contact pages:
            100

        About / Team / Director pages:
            80

        Normal pages:
            10
        """

        combined = (
            f"{url} {link_text}"
        ).lower()

        for keyword in CONTACT_KEYWORDS:

            if keyword in combined:

                return 100

        for keyword in IMPORTANT_KEYWORDS:

            if keyword in combined:

                return 80

        return 10

    def is_same_domain(
        self,
        base_url,
        target_url
    ):

        try:

            base_domain = urlparse(
                base_url
            ).netloc.lower().replace(
                "www.",
                ""
            )

            target_domain = urlparse(
                target_url
            ).netloc.lower().replace(
                "www.",
                ""
            )

            return (
                base_domain
                == target_domain
            )

        except Exception:

            return False

    def handle_error(self, failure):

        try:

            url = failure.request.url

        except Exception:

            url = "Unknown URL"

        print(
            f"[SCRAPY ERROR] "
            f"Failed: {url}"
        )

        print(
            f"[SCRAPY ERROR] "
            f"{failure.value}"
        )