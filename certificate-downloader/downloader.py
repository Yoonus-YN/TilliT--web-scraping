import asyncio
import os
from playwright.async_api import async_playwright


async def download_certificate(url, output_folder="downloads"):

    os.makedirs(output_folder, exist_ok=True)

    print(f"\n  Processing: {url}")

    try:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=True)

            context = await browser.new_context(accept_downloads=True)

            page = await context.new_page()

            # Inject a hook BEFORE page loads to intercept Blazor's downloadFromByteArray
            await page.add_init_script("""
                window.__captured_downloads = [];
                // Override the Blazor download function to capture file data
                const origFunc = window.downloadFromByteArray;
                Object.defineProperty(window, 'downloadFromByteArray', {
                    value: function(byteArray, fileName, contentType) {
                        window.__captured_downloads.push({
                            data: byteArray,
                            fileName: fileName,
                            contentType: contentType
                        });
                        // Also call original so the user sees the download in browser (if not headless)
                        if (typeof origFunc === 'function') {
                            origFunc(byteArray, fileName, contentType);
                        }
                    },
                    writable: true,
                    configurable: true
                });
            """)

            # Try loading page
            try:
                await page.goto(url, timeout=30000)
            except Exception as e:
                print("  Page failed to load")
                print(f"  {e}")
                await browser.close()
                return False

            # Wait for the SPA (Blazor) content to render
            await asyncio.sleep(3)

            # Re-hook the function after Blazor initializes (it may overwrite our hook)
            await page.evaluate("""
                if (!window.__download_hooked) {
                    const origFunc = window.downloadFromByteArray;
                    window.downloadFromByteArray = function(byteArray, fileName, contentType) {
                        window.__captured_downloads = window.__captured_downloads || [];
                        window.__captured_downloads.push({
                            data: byteArray,
                            fileName: fileName,
                            contentType: contentType
                        });
                        if (origFunc && origFunc !== window.downloadFromByteArray) {
                            origFunc(byteArray, fileName, contentType);
                        }
                    };
                    window.__download_hooked = true;
                }
            """)

            # Try finding the Print Certificate button
            try:
                button = await page.wait_for_selector(
                    "button.fsa-btn:has-text('Print Certificate')",
                    timeout=10000
                )
            except:
                # Fallback: try text selector
                try:
                    button = await page.wait_for_selector(
                        "text=Print Certificate",
                        timeout=5000
                    )
                except:
                    print("  'Print Certificate' button not found")
                    await browser.close()
                    return False

            # Click the button and wait for the download to be captured
            print("  Clicking 'Print Certificate'...")
            
            # Set up a download listener as a fallback (in case it triggers a real download)
            download_happened = False
            saved_path = None

            try:
                async with page.expect_download(timeout=15000) as download_info:
                    await button.click()
                
                # If we get here, it was a real browser download
                download = await download_info.value
                filename = download.suggested_filename
                saved_path = os.path.join(output_folder, filename)
                await download.save_as(saved_path)
                download_happened = True
                print(f"  Downloaded (browser): {saved_path}")
                
            except:
                # Not a real browser download — check if JS captured it
                await asyncio.sleep(5)  # Wait for Blazor to process
                
                captured = await page.evaluate("window.__captured_downloads || []")
                
                if captured:
                    for item in captured:
                        filename = item.get("fileName", "certificate.pdf")
                        data = item.get("data", "")
                        
                        if data:
                            # Blazor sends byte arrays as lists of integers
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
                else:
                    # Last resort: use page.pdf() to save as PDF
                    print("  No download detected, trying page PDF export...")
                    
                    # Try clicking Export to PDF link instead
                    try:
                        export_btn = await page.query_selector("text=Export to PDF")
                        if export_btn:
                            await export_btn.click()
                            await asyncio.sleep(5)
                            
                            captured = await page.evaluate("window.__captured_downloads || []")
                            if captured:
                                for item in captured:
                                    filename = item.get("fileName", "certificate.pdf")
                                    data = item.get("data", "")
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
                                        print(f"  Downloaded (Export to PDF): {saved_path}")
                    except Exception as ex:
                        print(f"  Export to PDF also failed: {ex}")

            if not download_happened:
                print("  Could not download the certificate.")

            await browser.close()
            return saved_path if download_happened else None

    except Exception as e:
        print("  Unexpected error occurred")
        print(f"  {e}")
        return None