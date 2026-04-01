import asyncio
import base64
import os
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext


class NopDownloader:
    """
    Persistent browser session for fast NOP certificate downloads.
    Keeps one Chromium instance alive across multiple downloads.
    """

    def __init__(self):
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._search_page = None
        self._search_ready = False

    async def start(self):
        """Launch browser once — reused for all downloads."""
        print("  \033[90mStarting browser engine...\033[0m", end="", flush=True)
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        print(" done")

    async def _ensure_search_page(self):
        """Navigate to the search page once, keep it ready for reuse."""
        if self._search_ready and self._search_page:
            # Clear previous search
            try:
                nop_input = await self._search_page.query_selector("#tbOperationId")
                if nop_input:
                    await nop_input.fill("")
                    return
            except Exception:
                pass

        # Need a fresh search page
        if self._search_page:
            try:
                await self._search_page.close()
            except Exception:
                pass

        self._search_page = await self._context.new_page()
        await self._search_page.goto(
            "https://organic.ams.usda.gov/integrity/Search",
            wait_until="domcontentloaded",
            timeout=90000,
        )

        # Wait for Blazor SPA input to appear
        nop_input = None
        for _ in range(30):
            await asyncio.sleep(1)
            nop_input = await self._search_page.query_selector("#tbOperationId")
            if nop_input:
                break

        if not nop_input:
            self._search_ready = False
            raise RuntimeError("Search page did not load")

        self._search_ready = True

    async def search_nop_id(self, nop_id: str) -> str | None:
        """Search for a NOP ID. Returns the OPP page URL or None."""
        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    self._search_ready = False
                    print(f"  Retrying search (attempt {attempt})...")

                await self._ensure_search_page()

                page = self._search_page
                nop_input = await page.query_selector("#tbOperationId")
                await nop_input.fill(nop_id)
                await asyncio.sleep(0.5)

                search_btn = await page.query_selector("button:has-text('Search')")
                if search_btn:
                    await search_btn.click()

                # Smart wait: poll for results instead of fixed sleep
                for _ in range(20):
                    await asyncio.sleep(1)
                    text = await page.evaluate("document.body.innerText")
                    if "of 0 items" in text or "items" in text or "No Records" in text:
                        break

                page_text = await page.evaluate("document.body.innerText")
                if "0 - 0 of 0 items" in page_text or "No Records Found" in page_text:
                    return None

                links = await page.evaluate("""
                    Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href.includes('OPP') && href.includes('nopid'))
                """)

                if links:
                    url = links[0]
                    if "&ret=" in url:
                        url = url.split("&ret=")[0]
                    return url

                return None

            except Exception as e:
                print(f"  Search error: {e}")
                self._search_ready = False
                if attempt >= max_retries:
                    return None
                await asyncio.sleep(2)

    async def download_certificate(self, url: str, output_folder: str, nop_id: str) -> str | None:
        """Download the certificate PDF from an OPP page. Returns saved file path."""
        os.makedirs(output_folder, exist_ok=True)
        page = await self._context.new_page()

        try:
            # Load OPP page
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"  Page load error: {e}")
                return None

            # Wait for Print Certificate button to appear (fast poll)
            button = None
            for _ in range(20):
                await asyncio.sleep(1)
                button = await page.query_selector("button:has-text('Print Certificate')")
                if button:
                    break

            if not button:
                # Fallback: try other selectors
                for sel in ["text=Print Certificate", "button.fsa-btn:has-text('Print')"]:
                    try:
                        button = await page.wait_for_selector(sel, timeout=3000)
                        if button:
                            break
                    except Exception:
                        continue

            default_filename = f"Certificate_{nop_id}.pdf" if nop_id else "certificate.pdf"

            if button:
                try:
                    async with page.expect_download(timeout=30000) as dl_info:
                        await button.click()
                    download = await dl_info.value
                    filename = download.suggested_filename or default_filename
                    saved_path = os.path.join(output_folder, filename)
                    await download.save_as(saved_path)
                    return saved_path
                except Exception:
                    pass

            # Fallback: Export to PDF
            try:
                export_btn = await page.wait_for_selector("text=Export to PDF", timeout=5000)
                if export_btn:
                    async with page.expect_download(timeout=20000) as dl_info:
                        await export_btn.click()
                    download = await dl_info.value
                    filename = download.suggested_filename or default_filename
                    saved_path = os.path.join(output_folder, filename)
                    await download.save_as(saved_path)
                    return saved_path
            except Exception:
                pass

            # Last resort: CDP print to PDF
            try:
                cdp = await self._context.new_cdp_session(page)
                result = await cdp.send("Page.printToPDF", {
                    "printBackground": True,
                    "preferCSSPageSize": True,
                })
                pdf_bytes = base64.b64decode(result["data"])
                saved_path = os.path.join(output_folder, default_filename)
                with open(saved_path, "wb") as f:
                    f.write(pdf_bytes)
                return saved_path
            except Exception:
                pass

            return None

        finally:
            await page.close()

    async def stop(self):
        """Close the browser."""
        try:
            if self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass