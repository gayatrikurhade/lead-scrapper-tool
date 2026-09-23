import json
import os
import subprocess
import sys
import tempfile

from bs4 import BeautifulSoup

SCRAPY_PROJECT = os.path.join(
    os.path.dirname(__file__),
    "scrapy_crawler"
)

def crawl_with_scrapy(website, max_pages=5):

    print("[SCRAPY] Starting:", website)
    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".json"
    )

    temp_file.close()
    print("[SCRAPY] Temp file:", temp_file.name)

    try:
        command = [
            sys.executable,
            "-m",
            "scrapy",
            "crawl",
            "website_spider",
            "-a",
            f"start_url={website}",
            "-a",
            f"max_pages={max_pages}",
            "-O",
            temp_file.name
        ]

        print("[SCRAPY] Running command...")
        result = subprocess.run(
            command,
            cwd=SCRAPY_PROJECT,
            capture_output=True,
            text=True,
            timeout=120
        )
        print("[SCRAPY] Return code:", result.returncode)
        print("[SCRAPY STDOUT]")
        print(result.stdout)

        print("[SCRAPY STDERR]")
        print(result.stderr)

        if result.returncode != 0:
            print("[SCRAPY] Crawl failed")
            return []

        if not os.path.exists(temp_file.name):
            print("[SCRAPY] JSON file does not exist")
            return []

        with open(
            temp_file.name,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        print("[SCRAPY] Raw pages:", len(data))

        pages = []

        for item in data:
            html = item.get("raw_html", "")
            if not html:
                continue
            soup = BeautifulSoup(
                html,
                "html.parser"
            )
            for tag in soup.find_all(
                ["script", "style", "noscript"]
            ):
                tag.decompose()
            text = soup.get_text(
                " ",
                strip=True
            )

            pages.append({
                "url": item.get("url", website),
                "soup": soup,
                "text": text,
                "raw_html": html
            })

        print(
            "[SCRAPY] Pages processed:",
            len(pages)
        )
        return pages

    except Exception as e:

        print(
            "[SCRAPY ERROR]",
            type(e).__name__,
            str(e)
        )
        return []

    finally:

        try:
            os.remove(temp_file.name)
        except Exception:
            pass
