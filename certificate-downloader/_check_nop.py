"""Check if specific NOP IDs exist in USDA database by searching directly."""
import asyncio
from playwright.async_api import async_playwright


async def check_nop_ids(nop_ids):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        for nop_id in nop_ids:
            page = await context.new_page()
            print(f"\n{'='*50}")
            print(f"Checking NOP ID: {nop_id}")
            print(f"{'='*50}")

            try:
                await page.goto(
                    "https://organic.ams.usda.gov/integrity/Search",
                    wait_until="domcontentloaded",
                    timeout=90000,
                )

                # Wait for Blazor
                nop_input = None
                for _ in range(30):
                    await asyncio.sleep(2)
                    nop_input = await page.query_selector("#tbOperationId")
                    if nop_input:
                        break

                if not nop_input:
                    print("  ERROR: Search page didn't load")
                    await page.close()
                    continue

                await nop_input.fill(nop_id)
                await asyncio.sleep(1)

                search_btn = await page.query_selector("button:has-text('Search')")
                if search_btn:
                    await search_btn.click()
                    await asyncio.sleep(10)

                # Get results text
                text = await page.evaluate("document.body.innerText")

                # Check result count
                import re
                match = re.search(r'(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\s+items', text)
                if match:
                    total = match.group(3)
                    print(f"  RESULT: {match.group(0)}")
                    if total == "0":
                        print(f"  >>> NOP ID {nop_id} DOES NOT EXIST in USDA database")
                    else:
                        # Get the operation name
                        links = await page.evaluate("""
                            Array.from(document.querySelectorAll('a'))
                                .filter(a => a.href.includes('OPP') && a.href.includes('nopid'))
                                .map(a => ({text: a.innerText.trim(), href: a.href}))
                        """)
                        if links:
                            print(f"  >>> EXISTS! Operation: {links[0]['text']}")
                            print(f"  >>> URL: {links[0]['href']}")
                        else:
                            print(f"  >>> EXISTS but no link found")
                else:
                    if "0 - 0 of 0 items" in text or "No Records" in text:
                        print(f"  >>> NOP ID {nop_id} DOES NOT EXIST in USDA database")
                    else:
                        print(f"  >>> Could not parse results")

            except Exception as e:
                print(f"  ERROR: {e}")
            finally:
                await page.close()

        await browser.close()


# Test the NOP ID user tried + several others from different certifiers
test_ids = [
    "6903966577",   # User's failing NOP ID
    "6903966799",   # Known working (EKOAGROS, Kazakhstan)
    "8699694577",   # Known working (different certifier)
    "2230010764",   # Known working
    "0106001021",   # Try a US domestic one
    "1937001000",   # Try another
    "0408001001",   # Try another
]

asyncio.run(check_nop_ids(test_ids))
