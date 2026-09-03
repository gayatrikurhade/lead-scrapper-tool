import re
import time
import random
import requests
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

DEFAULT_MAX_PAGES = 5
PAGE_TIMEOUT = 15000
PAGE_WAIT_MS = 500

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)

IMPORTANT_KEYWORDS = [
    "about",
    "about-us",
    "company",
    "contact",
    "team",
    "leadership",
    "management",
    "director",
    "who-we-are",
    "our-team",
    "our-people",
    "board",
    "profile"
]

def normalize_url(url):

    if not url:
        return ""

    url = url.strip()

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    return url.rstrip("/")

def is_same_domain(
    base_url,
    target_url
):

    try:

        base_domain = urlparse(
            base_url
        ).netloc.lower()

        target_domain = urlparse(
            target_url
        ).netloc.lower()

        base_domain = base_domain.replace(
            "www.",
            ""
        )

        target_domain = target_domain.replace(
            "www.",
            ""
        )

        return base_domain == target_domain

    except Exception:

        return False

def is_important_link(
    url,
    link_text=""
):

    combined = (
        f"{url} {link_text}"
    ).lower()

    return any(
        keyword in combined
        for keyword in IMPORTANT_KEYWORDS
    )

def crawl_website(
    website,
    max_pages=DEFAULT_MAX_PAGES
):

    website = normalize_url(
        website
    )

    if not website:
        return []

    pages = []

    visited = set()

    priority_queue = [website]
    normal_queue = []

    browser = None

    try:

        with sync_playwright() as p:

            try:

                browser = p.chromium.launch(
                    headless=True
                )

            except Exception as e:

                print(
                    "[PLAYWRIGHT START ERROR]"
                )

                print(
                    f"{type(e).__name__}: {e}"
                )

                print(
                    "Run:"
                )

                print(
                    "python -m playwright install chromium"
                )

                return []

            page = browser.new_page(
                viewport={
                    "width": 1366,
                    "height": 768
                },
                user_agent=USER_AGENT
            )

            while (
                (priority_queue or normal_queue)
                and len(pages) < max_pages
            ):

                if priority_queue:

                    current_url = (
                        priority_queue.pop(0)
                    )

                else:

                    current_url = (
                        normal_queue.pop(0)
                    )

                current_url = (
                    current_url
                    .split("#")[0]
                    .rstrip("/")
                )

                if current_url in visited:
                    continue

                if not is_same_domain(
                    website,
                    current_url
                ):
                    continue

                try:

                    print(
                        f"[CRAWLER] Opening: "
                        f"{current_url}"
                    )

                    page.goto(
                        current_url,
                        wait_until="domcontentloaded",
                        timeout=PAGE_TIMEOUT
                    )

                    page.wait_for_timeout(
                        PAGE_WAIT_MS
                    )

                    html = page.content()

                    final_url = page.url

                    print(
                        f"[CRAWLER] Loaded: "
                        f"{final_url}"
                    )

                except PlaywrightTimeoutError:

                    print(
                        f"[CRAWLER] Timeout: "
                        f"{current_url}"
                    )

                    visited.add(
                        current_url
                    )

                    continue

                except Exception as e:

                    print(
                        f"[CRAWLER] Page error: "
                        f"{current_url}"
                    )

                    print(
                        f"{type(e).__name__}: {e}"
                    )

                    visited.add(
                        current_url
                    )

                    continue

                visited.add(
                    current_url
                )

                soup = BeautifulSoup(
                    html,
                    "html.parser"
                )

                text_soup = BeautifulSoup(
                    html,
                    "html.parser"
                )

                for tag in text_soup(
                    [
                        "script",
                        "style",
                        "noscript"
                    ]
                ):

                    tag.decompose()

                text = text_soup.get_text(
                    " ",
                    strip=True
                )

                pages.append({

                    "url": final_url,

                    "soup": soup,

                    "text": text,

                    "raw_html": html
                })

                print(
                    f"[CRAWLER] Saved page "
                    f"{len(pages)}/{max_pages}: "
                    f"{final_url}"
                )

                priority_links = []
                normal_links = []

                for link in soup.find_all(
                    "a",
                    href=True
                ):

                    href = link.get(
                        "href",
                        ""
                    ).strip()

                    if not href:
                        continue

                    if href.startswith(
                        (
                            "mailto:",
                            "tel:",
                            "javascript:",
                            "#"
                        )
                    ):
                        continue

                    full_url = urljoin(
                        final_url,
                        href
                    )

                    full_url = (
                        full_url
                        .split("#")[0]
                        .rstrip("/")
                    )

                    parsed = urlparse(
                        full_url
                    )

                    if parsed.scheme not in (
                        "http",
                        "https"
                    ):
                        continue

                    if not is_same_domain(
                        website,
                        full_url
                    ):
                        continue

                    if full_url in visited:
                        continue

                    link_text = link.get_text(
                        " ",
                        strip=True
                    )

                    if is_important_link(
                        full_url,
                        link_text
                    ):

                        priority_links.append(
                            full_url
                        )

                    else:

                        normal_links.append(
                            full_url
                        )

                for link in priority_links:

                    if (
                        link not in priority_queue
                        and link not in normal_queue
                        and link not in visited
                    ):

                        priority_queue.append(
                            link
                        )

                for link in normal_links:

                    if (
                        link not in priority_queue
                        and link not in normal_queue
                        and link not in visited
                    ):

                        normal_queue.append(
                            link
                        )

            if browser:

                browser.close()

                browser = None

    except Exception as e:

        print(
            "[CRAWLER ERROR]"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        if browser:

            try:
                browser.close()
            except Exception:
                pass

    return pages

def extract_emails(pages):

    emails = set()

    email_pattern = re.compile(
        r"[A-Za-z0-9._%+-]+"
        r"@[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}"
    )

    for page in pages:

        found = email_pattern.findall(
            page["text"]
        )

        emails.update(
            found
        )

        for link in page["soup"].find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            ).strip()

            if href.lower().startswith(
                "mailto:"
            ):

                email = (
                    href[7:]
                    .split("?")[0]
                    .strip()
                )

                if email:

                    emails.add(
                        email
                    )

    return sorted(
        emails
    )

def clean_phone(phone):

    if not phone:
        return ""

    phone = phone.strip()

    return re.sub(
        r"[^\d+]",
        "",
        phone
    )

def extract_phones(pages):

    phones = set()

    mobile_pattern = re.compile(
        r"(?:\+91[\s-]?)?[6-9]\d{9}"
    )

    for page in pages:

        found = mobile_pattern.findall(
            page["text"]
        )

        for phone in found:

            cleaned = clean_phone(
                phone
            )

            if cleaned:

                phones.add(
                    cleaned
                )

        for link in page["soup"].find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            ).strip()

            if href.lower().startswith(
                "tel:"
            ):

                phone = clean_phone(
                    href[4:]
                )

                if phone:

                    phones.add(
                        phone
                    )

    return sorted(
        phones
    )

def extract_director(pages):

    titles = [
        "managing director",
        "executive director",
        "whole time director",
        "director",
        "founder & ceo",
        "co-founder",
        "founder",
        "chief executive officer",
        "ceo",
        "managing partner",
        "proprietor",
        "owner"
    ]

    titles_sorted = sorted(
        titles,
        key=len,
        reverse=True
    )

    title_pattern = "|".join(
        re.escape(t) for t in titles_sorted
    )

    stopwords = {
        "director", "directors", "founder", "founders", "co-founder",
        "ceo", "cto", "coo", "cfo", "chief", "executive", "officer",
        "officers", "managing", "partner", "partners", "proprietor",
        "owner", "owners", "whole", "time",
        "is", "the", "of", "and", "a", "an", "our", "we", "this",
        "that", "with", "for", "in", "on", "at", "as", "by", "to",
        "from", "was", "are", "will", "has", "have", "had", "get",
        "touch", "contact", "speak", "want", "need", "would", "you",
        "your"
    }

    stop_pattern = "|".join(
        re.escape(w) for w in stopwords
    )

    name_word = (
        rf"(?!(?:{stop_pattern})\b)"
        r"[A-Z][A-Za-z.'-]+"
    )

    name_re = (
        rf"{name_word}(?:\s+{name_word}){{1,3}}"
    )

    patterns = [

        re.compile(
            rf"(?:{title_pattern})"
            rf"\s*[:\-–]\s*"
            rf"(?:mr\.?|ms\.?|mrs\.?|dr\.?)?\s*"
            rf"({name_re})",
            re.IGNORECASE
        ),

        re.compile(
            rf"(?:{title_pattern})"
            rf"\s+"
            rf"(?:mr\.?|ms\.?|mrs\.?|dr\.?)?\s*"
            rf"({name_re})",
            re.IGNORECASE
        ),

        re.compile(
            rf"({name_re})"
            rf"\s*[,\-–]\s*"
            rf"(?:{title_pattern})\b",
            re.IGNORECASE
        ),

        re.compile(
            rf"({name_re})"
            rf"\s+"
            rf"(?:{title_pattern})\b",
            re.IGNORECASE
        ),

        re.compile(
            rf"({name_re})"
            rf"\s+is\s+(?:the\s+)?"
            rf"(?:{title_pattern})\b",
            re.IGNORECASE
        )
    ]

    ignored_names = {
        "Director",
        "Managing Director",
        "Executive Director",
        "Board Director",
        "Our Director",
        "The Director",
        "Our Management",
        "Our Team",
        "Team Members",
        "Digital Card",
        "Our History",
        "Founder Ceo",
        "Co Founder",
        "Chief Executive",
        "Managing Partner"
    }

    for page in pages:

        text = page["text"]

        for pattern in patterns:

            match = pattern.search(
                text
            )

            if not match:
                continue

            name = match.group(
                1
            ).strip()

            if name.title() in {
                n.title() for n in ignored_names
            }:
                continue

            if len(name.split()) < 2:
                continue

            print(
                f"[DIRECTOR] Found '{name}' on {page['url']} "
                f"via text pattern"
            )

            return name

    print(
        "[DIRECTOR] No match via text patterns, "
        "trying heading-based search..."
    )

    for page in pages:

        soup = page["soup"]

        elements = soup.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "strong",
                "b",
                "span"
            ]
        )

        for element in elements:

            heading = element.get_text(
                " ",
                strip=True
            )

            heading_lower = heading.lower()

            if not any(
                title in heading_lower
                for title in titles
            ):
                continue

            parent = element.parent

            if not parent:
                continue

            block_text = parent.get_text(
                " ",
                strip=True
            )

            match = re.search(
                rf"\b(?:Mr\.|Ms\.|Mrs\.|Dr\.)?\s*({name_re})\b",
                block_text
            )

            if not match:
                continue

            name = match.group(
                1
            ).strip()

            if name.title() in {
                n.title() for n in ignored_names
            }:
                continue

            if len(name.split()) < 2:
                continue

            print(
                f"[DIRECTOR] Found '{name}' on {page['url']} "
                f"via heading '{heading}'"
            )

            return name

    print(
        "[DIRECTOR] No leadership name found on any crawled page "
        "(the site may simply not list one, or it's on a page "
        "outside max_pages)"
    )

    return "Not Found"

def extract_linkedin_url(pages):

    linkedin_urls = set()

    for page in pages:

        soup = page["soup"]

        for link in soup.find_all(
            "a",
            href=True
        ):

            href = link.get(
                "href",
                ""
            ).strip()

            if "linkedin.com/company" not in (
                href.lower()
            ):
                continue

            full_url = urljoin(
                page["url"],
                href
            )

            parsed = urlparse(
                full_url
            )

            path = parsed.path.rstrip("/")

            if "/company/" not in (
                path.lower()
            ):
                continue

            clean_url = (
                "https://www.linkedin.com"
                + path
                + "/"
            )

            linkedin_urls.add(
                clean_url
            )

    if linkedin_urls:

        return sorted(
            linkedin_urls
        )[0]

    return "Not Found"

def extract_followers_from_text(text):

    patterns = [

        r"([\d,.]+)\s*([KkMmBb])?\s*\+?\s*followers",

        r"followers\s*[:\-]?\s*"
        r"([\d,.]+)\s*([KkMmBb])?"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        number = (
            match.group(1)
            .replace(",", "")
            .strip()
        )

        suffix = match.group(2)

        try:

            value = float(
                number
            )

            if suffix:

                suffix = suffix.lower()

                if suffix == "k":
                    value *= 1000

                elif suffix == "m":
                    value *= 1000000

                elif suffix == "b":
                    value *= 1000000000

            return str(
                int(value)
            )

        except (
            ValueError,
            TypeError
        ):

            continue

    return "Not Found"

def get_followers(pages):
    """
    Cheap first pass: scan the pages we already crawled from the
    company's own website in case a follower count happens to be
    embedded there (rare, but free since we already have the HTML).
    """

    for page in pages:

        text = " ".join(
            page.get(
                "text",
                ""
            ).split()
        )

        followers = extract_followers_from_text(
            text
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - TEXT] "
                f"{followers}"
            )

            return followers

        raw_html = page.get(
            "raw_html",
            ""
        )

        if raw_html:

            followers = extract_followers_from_text(
                raw_html
            )

            if followers != "Not Found":

                print(
                    f"[FOLLOWERS FOUND - HTML] "
                    f"{followers}"
                )

                return followers

    return "Not Found"

def get_linkedin_followers_direct(linkedin_url):
    """
    Primary approach, no search engine and no API involved: fetch
    the LinkedIn company page's raw HTML directly with a plain HTTP
    request (not a headless browser). LinkedIn server-renders a
    <meta name="description"> / <meta property="og:description">
    tag containing something like "1,234 followers on LinkedIn..."
    so Google can index it — that tag is present in the initial
    HTML response, before any JavaScript runs.

    A headless browser actually works against us here: Playwright
    executes LinkedIn's JS, which is what triggers the redirect to
    the login/authwall. A plain requests.get() never runs that JS,
    so it just gets the raw server response with the meta tags
    still intact.
    """

    if linkedin_url == "Not Found":
        return "Not Found"

    headers = {

        "User-Agent": USER_AGENT,

        "Accept-Language": "en-US,en;q=0.9",

        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        )
    }

    try:

        print(
            f"[LINKEDIN DIRECT] Fetching: {linkedin_url}"
        )

        response = requests.get(
            linkedin_url,
            headers=headers,
            timeout=15
        )

        print(
            f"[LINKEDIN DIRECT] Status: {response.status_code}, "
            f"length: {len(response.text)} chars"
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        meta_texts = []

        meta_desc = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        if meta_desc and meta_desc.get("content"):

            meta_texts.append(
                meta_desc["content"]
            )

        og_desc = soup.find(
            "meta",
            attrs={"property": "og:description"}
        )

        if og_desc and og_desc.get("content"):

            meta_texts.append(
                og_desc["content"]
            )

        combined = " ".join(meta_texts)

        if combined:

            print(
                f"[LINKEDIN DIRECT] Meta description: {combined[:200]}"
            )

        followers = extract_followers_from_text(
            combined
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - LINKEDIN DIRECT - META] {followers}"
            )

            return followers

        followers = extract_followers_from_text(
            response.text
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - LINKEDIN DIRECT - HTML] {followers}"
            )

        else:

            print(
                "[LINKEDIN DIRECT] No follower count in meta tags or HTML "
                "(likely served a login/authwall page instead)"
            )

        return followers

    except Exception as e:

        print(
            f"[LINKEDIN DIRECT ERROR] {e}"
        )

        return "Not Found"

def build_followers_query(linkedin_url, company_name):
    """
    Prefer a natural-language query (company name) over an exact
    quoted URL — search engines tend to return thin/near-empty
    results pages for exact-URL phrase searches, but return normal
    snippet-rich results for a plain company-name query.
    """

    if company_name:

        return f"{company_name} linkedin followers"

    if linkedin_url != "Not Found":

        slug = (
            linkedin_url
            .rstrip("/")
            .split("/company/")[-1]
        )

        slug_name = slug.replace("-", " ")

        return f"{slug_name} linkedin followers"

    return None

def get_followers_via_duckduckgo(linkedin_url, company_name, browser):
    """
    Primary fallback: DuckDuckGo's plain HTML endpoint has no
    JavaScript, no cookie-consent wall, and is far less likely to
    block a headless browser than Google is. Snippet text is pulled
    from LinkedIn's own meta description, so it usually still
    contains "X followers".
    """

    query = build_followers_query(
        linkedin_url,
        company_name
    )

    if not query:
        return "Not Found"

    search_url = (
        "https://html.duckduckgo.com/html/?q="
        + query.replace(" ", "+")
    )

    page = browser.new_page(
        user_agent=USER_AGENT
    )

    try:

        print(
            f"[DUCKDUCKGO] Searching: {query}"
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            PAGE_WAIT_MS
        )

        text = page.content()

        print(
            f"[DUCKDUCKGO] Landed on: {page.url}"
        )

        print(
            f"[DUCKDUCKGO] Result page length: {len(text)} chars"
        )

        if len(text) < 1000:

            print(
                f"[DUCKDUCKGO] SHORT RESPONSE DUMP: {text[:1000]}"
            )

        followers = extract_followers_from_text(
            text
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - DUCKDUCKGO] {followers}"
            )

            return followers

        snippet_soup = BeautifulSoup(text, "html.parser")

        snippets = snippet_soup.find_all(
            "a",
            class_="result__snippet"
        )

        preview = " | ".join(
            s.get_text(" ", strip=True)
            for s in snippets[:3]
        )

        print(
            f"[DUCKDUCKGO] No follower count in snippets "
            f"({len(snippets)} snippets found). "
            f"Preview: {preview[:300]}"
        )

        return "Not Found"

    except Exception as e:

        print(
            f"[DUCKDUCKGO SEARCH ERROR] {e}"
        )

        return "Not Found"

    finally:

        page.close()

def get_followers_via_duckduckgo_lite(linkedin_url, company_name, browser):
    """
    Second attempt on DuckDuckGo: the "lite" endpoint is an even
    more minimal, table-based HTML page intended for very old
    browsers / accessibility tools. It's sometimes served when the
    main html.duckduckgo.com endpoint returns nothing useful.
    """

    query = build_followers_query(
        linkedin_url,
        company_name
    )

    if not query:
        return "Not Found"

    search_url = (
        "https://lite.duckduckgo.com/lite/?q="
        + query.replace(" ", "+")
    )

    page = browser.new_page(
        user_agent=USER_AGENT
    )

    try:

        print(
            f"[DUCKDUCKGO-LITE] Searching: {query}"
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            PAGE_WAIT_MS
        )

        text = page.content()

        print(
            f"[DUCKDUCKGO-LITE] Result page length: {len(text)} chars"
        )

        if len(text) < 1000:

            print(
                f"[DUCKDUCKGO-LITE] SHORT RESPONSE DUMP: {text[:1000]}"
            )

        followers = extract_followers_from_text(
            text
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - DUCKDUCKGO-LITE] {followers}"
            )

        return followers

    except Exception as e:

        print(
            f"[DUCKDUCKGO-LITE SEARCH ERROR] {e}"
        )

        return "Not Found"

    finally:

        page.close()

def get_followers_via_google(linkedin_url, company_name, browser):
    """
    Secondary fallback, only used if DuckDuckGo comes up empty.
    Google is more likely to show a cookie-consent screen or a
    CAPTCHA to a fresh headless browser, so we try to click through
    a basic consent dialog if one appears.
    """

    query = build_followers_query(
        linkedin_url,
        company_name
    )

    if not query:
        return "Not Found"

    search_url = (
        "https://www.google.com/search?hl=en&gl=us&q="
        + query.replace(" ", "+").replace('"', "%22")
    )

    page = browser.new_page(
        user_agent=USER_AGENT
    )

    try:

        print(
            f"[GOOGLE] Searching: {query}"
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=PAGE_TIMEOUT
        )

        page.wait_for_timeout(
            PAGE_WAIT_MS
        )

        for consent_text in ("Accept all", "I agree", "Accept"):

            try:

                button = page.get_by_role(
                    "button",
                    name=consent_text
                )

                if button.count() > 0:

                    button.first.click(
                        timeout=2000
                    )

                    page.wait_for_timeout(
                        PAGE_WAIT_MS
                    )

                    print(
                        f"[GOOGLE] Clicked consent button: "
                        f"{consent_text}"
                    )

                    break

            except Exception:

                continue

        print(
            f"[GOOGLE] Landed on: {page.url}"
        )

        if (
            "sorry/index" in page.url
            or "consent.google" in page.url
        ):

            print(
                "[GOOGLE] Blocked (captcha/consent wall)"
            )

            return "Not Found"

        text = page.content()

        followers = extract_followers_from_text(
            text
        )

        if followers != "Not Found":

            print(
                f"[FOLLOWERS FOUND - GOOGLE] {followers}"
            )

        return followers

    except Exception as e:

        print(
            f"[GOOGLE SEARCH ERROR] {e}"
        )

        return "Not Found"

    finally:

        page.close()

def fetch_linkedin_followers(linkedin_url, company_name):
    """
    Order of attempts:
    1. Direct plain-HTTP fetch of the LinkedIn page's meta tags
       (no browser, no search engine — most likely to work).
    2. DuckDuckGo HTML / lite (kept as a fallback, though currently
       blocking automated traffic).
    3. Google (kept as a last resort, though currently CAPTCHA'd).
    """

    followers = get_linkedin_followers_direct(
        linkedin_url
    )

    if followers != "Not Found":
        return followers

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        try:

            followers = get_followers_via_duckduckgo(
                linkedin_url,
                company_name,
                browser
            )

            if followers != "Not Found":
                return followers

            followers = get_followers_via_duckduckgo_lite(
                linkedin_url,
                company_name,
                browser
            )

            if followers != "Not Found":
                return followers

            return get_followers_via_google(
                linkedin_url,
                company_name,
                browser
            )

        finally:

            browser.close()

def analyze_website(
    company,
    website,
    max_pages=DEFAULT_MAX_PAGES
):

    print(
        f"\n[ANALYZING] {company}"
    )

    website = normalize_url(
        website
    )

    if not website:

        return {
            "Company": company,
            "Email": "Not Found",
            "Phone": "Not Found",
            "Director": "Not Found",
            "LinkedIn URL": "Not Found",
            "LinkedIn Followers": "Not Found"
        }

    pages = crawl_website(
        website,
        max_pages=max_pages
    )

    if not pages:

        print(
            f"[NO DATA] Could not crawl: "
            f"{website}"
        )

        return {
            "Company": company,
            "Email": "Not Found",
            "Phone": "Not Found",
            "Director": "Not Found",
            "LinkedIn URL": "Not Found",
            "LinkedIn Followers": "Not Found"
        }

    emails = extract_emails(
        pages
    )

    phones = extract_phones(
        pages
    )

    director = extract_director(
        pages
    )

    linkedin_url = extract_linkedin_url(
        pages
    )

    linkedin_followers = get_followers(
        pages
    )

    if linkedin_followers == "Not Found":

        linkedin_followers = fetch_linkedin_followers(
            linkedin_url,
            company
        )

    return {

        "Company":
            company,

        "Email":
            (
                ", ".join(emails)
                if emails
                else "Not Found"
            ),

        "Phone":
            (
                ", ".join(phones)
                if phones
                else "Not Found"
            ),

        "Director":
            director,

        "LinkedIn URL":
            linkedin_url,

        "LinkedIn Followers":
            linkedin_followers
    }

if __name__ == "__main__":

    print(
        "=========================================="
    )

    print(
        " WEBSITE CRAWLER V2 TEST"
    )

    print(
        "=========================================="
    )

    company = input(
        "\nEnter company name: "
    ).strip()

    website = input(
        "Enter company website: "
    ).strip()

    result = analyze_website(
        company=company,
        website=website,
        max_pages=5
    )

    print(
        "\n=========================================="
    )

    print(
        "RESULT"
    )

    print(
        "=========================================="
    )

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )




    




        




