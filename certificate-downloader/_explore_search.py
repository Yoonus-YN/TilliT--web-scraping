"""Explore the search page to find all input fields."""
import asyncio
from playwright.async_api import async_playwright


async def main():
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
        page = await context.new_page()

        await page.goto(
            "https://organic.ams.usda.gov/integrity/Search",
            wait_until="domcontentloaded",
            timeout=90000,
        )

        for _ in range(30):
            await asyncio.sleep(2)
            nop_input = await page.query_selector("#tbOperationId")
            if nop_input:
                break

        # Get ALL input fields and their IDs
        inputs = await page.evaluate("""
            Array.from(document.querySelectorAll('input, select, textarea')).map(el => ({
                tag: el.tagName,
                id: el.id,
                name: el.name || '',
                type: el.type || '',
                placeholder: el.placeholder || '',
                label: (() => {
                    if (el.id) {
                        const lbl = document.querySelector('label[for="' + el.id + '"]');
                        if (lbl) return lbl.innerText.trim();
                    }
                    // Check previous sibling or parent for label
                    const parent = el.closest('.fsa-field');
                    if (parent) {
                        const lbl = parent.querySelector('label, .fsa-field__label');
                        if (lbl) return lbl.innerText.trim();
                    }
                    return '';
                })(),
                visible: el.offsetParent !== null
            }))
        """)
        
        print("=== All inputs on search page ===")
        for inp in inputs:
            vis = "visible" if inp['visible'] else "HIDDEN"
            print(f"  <{inp['tag']}> id={inp['id']} name={inp['name']} type={inp['type']} placeholder='{inp['placeholder']}' label='{inp['label']}' [{vis}]")

        # Get all collapsible section headers
        headers = await page.evaluate("""
            Array.from(document.querySelectorAll('[class*="panelbar"], [class*="collapse"], [role="button"], .fsa-panel, h3, h4, legend'))
                .map(el => ({
                    tag: el.tagName,
                    text: el.innerText.trim().substring(0, 100),
                    classes: el.className.substring(0, 100),
                    id: el.id
                }))
                .filter(el => el.text.length > 0)
        """)
        print(f"\n=== Section headers ({len(headers)}) ===")
        for h in headers:
            print(f"  <{h['tag']}> [{h['text']}] class={h['classes'][:60]} id={h['id']}")

        # Try expanding "Operation Information" section
        print("\n=== Trying to expand Operation Information ===")
        op_section = await page.query_selector("text=Operation Information")
        if op_section:
            await op_section.click()
            await asyncio.sleep(2)
            print("  Clicked! Checking for new inputs...")
            
            inputs2 = await page.evaluate("""
                Array.from(document.querySelectorAll('input, select, textarea'))
                    .filter(el => el.offsetParent !== null)
                    .map(el => ({
                        id: el.id,
                        type: el.type || '',
                        placeholder: el.placeholder || '',
                        label: (() => {
                            const parent = el.closest('.fsa-field');
                            if (parent) {
                                const lbl = parent.querySelector('label, .fsa-field__label');
                                if (lbl) return lbl.innerText.trim();
                            }
                            return '';
                        })()
                    }))
            """)
            print(f"  Visible inputs after expanding:")
            for inp in inputs2:
                print(f"    id={inp['id']} type={inp['type']} placeholder='{inp['placeholder']}' label='{inp['label']}'")

        # Also check the visible page text
        text = await page.evaluate("document.body.innerText")
        # Find text near "NOP" or "Operation"
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'NOP' in line or 'Operation Name' in line or 'Operation ID' in line:
                print(f"\n  Text line {i}: {line.strip()}")

        await browser.close()


asyncio.run(main())
