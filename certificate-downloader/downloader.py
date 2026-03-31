import asyncio
import os
import re
from playwright.async_api import async_playwright


async def download_certificate(url, output_folder="downloads", nop_id=""):
    """
    Download a certificate PDF from the USDA NOP Integrity Database.
    Uses Playwright to handle the Blazor SPA and intercept PDF downloads.
    Returns the saved file path on success, None on failure.
    """
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n  Processing: {url}")

    try:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=True)

            context = await browser.new_context(
                accept_downloads=True,
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )

            page = await context.new_page()

            # Intercept network responses to catch PDF data directly
            pdf_responses = []

            async def handle_response(response):
                content_type = response.headers.get("content-type", "")
                if "pdf" in content_type or response.url.endswith(".pdf"):
                    try:
                        body = await response.body()
                        pdf_responses.append({
                            "data": body,
                            "url": response.url,
                        })
                    except Exception:
                        pass

            page.on("response", handle_response)

            # Inject JS hook BEFORE page loads to capture Blazor downloads
            await page.add_init_script("""
                window.__captured_downloads = [];
                
                // Hook downloadFromByteArray (Blazor's download method)
                const hookDownload = () => {
                    if (window.__hooked) return;
                    const orig = window.downloadFromByteArray;
                    window.downloadFromByteArray = function(byteArray, fileName, contentType) {
                        window.__captured_downloads.push({
                            data: Array.from(byteArray),
                            fileName: fileName,
                            contentType: contentType
                        });
                        if (orig && typeof orig === 'function') {
                            orig(byteArray, fileName, contentType);
                        }
                    };
                    window.__hooked = true;
                };
                
                hookDownload();
                
                // Re-hook periodically in case Blazor overwrites it
                setInterval(hookDownload, 500);
            """)

            # Load the page
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception:
                # Even if timeout, page might still be usable
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print(f"  Page failed to load: {e}")
                    await browser.close()
                    return None

            # Wait for Blazor SPA to fully render
            print("  Waiting for page to render...")
            for _ in range(15):
                await asyncio.sleep(1)
                # Check if key content is visible
                has_content = await page.evaluate("""
                    document.body.innerText.includes('Print Certificate') ||
                    document.body.innerText.includes('Export to PDF') ||
                    document.body.innerText.includes('Certificate') ||
                    document.querySelector('[class*="certificate"]') !== null
                """)
                if has_content:
                    break

            # Re-hook after Blazor has initialized
            await page.evaluate("""
                if (!window.__hooked) {
                    const orig = window.downloadFromByteArray;
                    window.downloadFromByteArray = function(byteArray, fileName, contentType) {
                        window.__captured_downloads = window.__captured_downloads || [];
                        window.__captured_downloads.push({
                            data: Array.from(byteArray),
                            fileName: fileName,
                            contentType: contentType
                        });
                        if (orig && typeof orig === 'function' && orig !== window.downloadFromByteArray) {
                            orig(byteArray, fileName, contentType);
                        }
                    };
                    window.__hooked = true;
                }
            """)

            # Check if the page has valid certificate data
            page_text = await page.evaluate("document.body.innerText")
            if "no records found" in page_text.lower() or "no results" in page_text.lower():
                print("  No certificate found for this NOP ID.")
                await browser.close()
                return None

            download_happened = False
            saved_path = None
            default_filename = f"{nop_id}_OperationProfile.pdf" if nop_id else "certificate.pdf"

            # --- Strategy 1: Click "Export to PDF" link ---
            print("  Looking for Export to PDF...")
            try:
                export_btn = await page.wait_for_selector(
                    "text=Export to PDF", timeout=8000
                )
                if export_btn:
                    print("  Clicking 'Export to PDF'...")
                    try:
                        async with page.expect_download(timeout=20000) as dl_info:
                            await export_btn.click()
                        download = await dl_info.value
                        filename = download.suggested_filename or default_filename
                        saved_path = os.path.join(output_folder, filename)
                        await download.save_as(saved_path)
                        download_happened = True
                        print(f"  Downloaded (browser download): {saved_path}")
                    except Exception:
                        # Download might be via JS, not browser download
                        await asyncio.sleep(5)
            except Exception:
                pass

            # --- Strategy 2: Click "Print Certificate" button ---
            if not download_happened:
                print("  Looking for Print Certificate button...")
                try:
                    button = None
                    for selector in [
                        "button:has-text('Print Certificate')",
                        "a:has-text('Print Certificate')",
                        "text=Print Certificate",
                        "[onclick*='Print']",
                        "button.fsa-btn:has-text('Print')",
                    ]:
                        try:
                            button = await page.wait_for_selector(selector, timeout=3000)
                            if button:
                                break
                        except Exception:
                            continue

                    if button:
                        print("  Clicking 'Print Certificate'...")
                        try:
                            async with page.expect_download(timeout=20000) as dl_info:
                                await button.click()
                            download = await dl_info.value
                            filename = download.suggested_filename or default_filename
                            saved_path = os.path.join(output_folder, filename)
                            await download.save_as(saved_path)
                            download_happened = True
                            print(f"  Downloaded (browser download): {saved_path}")
                        except Exception:
                            await asyncio.sleep(5)
                except Exception:
                    pass

            # --- Strategy 3: Check JS captured downloads ---
            if not download_happened:
                captured = await page.evaluate("window.__captured_downloads || []")
                if captured:
                    print(f"  Found {len(captured)} JS-captured download(s)...")
                    for item in captured:
                        filename = item.get("fileName", default_filename)
                        data = item.get("data", [])
                        if data:
                            if isinstance(data, list):
                                pdf_bytes = bytes(data)
                            elif isinstance(data, str):
                                import base64
                                pdf_bytes = base64.b64decode(data)
                            else:
                                continue
                            saved_path = os.path.join(output_folder, filename)
                            with open(saved_path, "wb") as f:
                                f.write(pdf_bytes)
                            download_happened = True
                            print(f"  Downloaded (JS capture): {saved_path}")
                            break

            # --- Strategy 4: Check intercepted network PDF responses ---
            if not download_happened and pdf_responses:
                print(f"  Found {len(pdf_responses)} PDF response(s) from network...")
                for resp in pdf_responses:
                    saved_path = os.path.join(output_folder, default_filename)
                    with open(saved_path, "wb") as f:
                        f.write(resp["data"])
                    download_happened = True
                    print(f"  Downloaded (network intercept): {saved_path}")
                    break

            # --- Strategy 5: Screenshot the page as PDF (last resort) ---
            if not download_happened:
                print("  Trying direct PDF export of the page...")
                try:
                    # Use CDP to print page as PDF
                    cdp = await context.new_cdp_session(page)
                    result = await cdp.send("Page.printToPDF", {
                        "printBackground": True,
                        "preferCSSPageSize": True,
                    })
                    import base64
                    pdf_bytes = base64.b64decode(result["data"])
                    saved_path = os.path.join(output_folder, default_filename)
                    with open(saved_path, "wb") as f:
                        f.write(pdf_bytes)
                    download_happened = True
                    print(f"  Downloaded (page PDF export): {saved_path}")
                except Exception as ex:
                    print(f"  PDF export failed: {ex}")

            if not download_happened:
                print("  Could not download the certificate.")

            await browser.close()
            return saved_path if download_happened else None

    except Exception as e:
        print(f"  Unexpected error: {e}")
        return None