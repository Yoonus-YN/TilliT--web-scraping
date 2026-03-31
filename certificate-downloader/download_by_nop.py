import asyncio
import os
import sys
import time
import webbrowser
from winotify import Notification, audio

# Fix imports so this works from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from downloader import download_certificate


def notify(title, message, file_path=None):
    """Show a Windows desktop notification with optional Open file action."""
    toast = Notification(
        app_id="NOP Certificate Downloader",
        title=title,
        msg=message,
        duration="short",
    )
    toast.set_audio(audio.Default, loop=False)
    if file_path:
        toast.add_actions(label="Open file", launch=file_path)
        toast.add_actions(label="Open folder", launch=os.path.dirname(file_path))
    toast.show()


def print_banner():
    print()
    print("\033[36m" + "=" * 60 + "\033[0m")
    print("\033[36m" + "   ╔╦╗╦╦  ╦  ╦╔╦╗  ─  NOP Certificate Downloader" + "\033[0m")
    print("\033[36m" + "    ║ ║║  ║  ║ ║   ─  USDA Organic Integrity Database" + "\033[0m")
    print("\033[36m" + "    ╩ ╩╩═╝╩═╝╩ ╩   ─  Web Scraping Tool v2.0" + "\033[0m")
    print("\033[36m" + "=" * 60 + "\033[0m")


async def main():
    # Downloads go to the device's default Downloads folder
    output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_folder, exist_ok=True)

    # The search URL works for ALL certifiers — no cid needed
    search_url: str = "https://organic.ams.usda.gov/integrity/Api/Search?keyword="
    cert_url: str = "https://organic.ams.usda.gov/integrity/CP/OPP?cid={cid}&nopid={nop}"
    downloaded_count: int = 0
    failed_count: int = 0

    print_banner()
    print(f"\033[33m  Downloads folder: {os.path.abspath(output_folder)}\033[0m")
    print("\033[90m  Type a NOP ID to download, or S to stop.\033[0m")
    print("\033[36m" + "-" * 60 + "\033[0m")

    while True:
        print()
        user_input: str = input("\033[1m  Enter NOP ID (or S to stop): \033[0m").strip()

        # Stop condition
        if user_input.upper() == "S":
            print()
            print("\033[36m" + "-" * 60 + "\033[0m")
            print(f"\033[32m  ✓ Downloaded: {downloaded_count} certificate(s)\033[0m")
            if failed_count:
                print(f"\033[31m  ✗ Failed: {failed_count}\033[0m")
            print(f"\033[33m  Saved to: {os.path.abspath(output_folder)}\033[0m")
            print("\033[36m" + "=" * 60 + "\033[0m")
            break

        # Validate input
        if not user_input:
            print("  \033[31m[!] NOP ID cannot be empty. Try again.\033[0m")
            continue

        start_time = time.time()

        # --- Step 1: Lookup the NOP ID via the API to find the correct certifier ID ---
        print(f"  \033[90mSearching for NOP ID: {user_input} ...\033[0m")

        full_url = None
        try:
            import requests
            api_url = f"{search_url}{user_input}"
            resp = requests.get(api_url, timeout=15)
            if resp.status_code == 200:
                results = resp.json()
                # Find exact NOP ID match
                for item in results:
                    op_nop = str(item.get("op_nopOpID", ""))
                    if op_nop == user_input:
                        cid = item.get("ci_certId", "")
                        if cid:
                            full_url = cert_url.format(cid=cid, nop=user_input)
                        break
                if not full_url and results:
                    # Use first result if no exact match
                    cid = results[0].get("ci_certId", "")
                    if cid:
                        full_url = cert_url.format(cid=cid, nop=user_input)
        except Exception:
            pass

        # Fallback: use default URL format
        if not full_url:
            full_url = f"https://organic.ams.usda.gov/integrity/CP/OPP?cid=87&nopid={user_input}"

        # --- Step 2: Open in browser ---
        print(f"  \033[94m[>>] Opening: {full_url}\033[0m")
        webbrowser.open(full_url)

        # --- Step 3: Download the certificate via Playwright ---
        try:
            saved_path = await download_certificate(
                full_url, output_folder=output_folder, nop_id=user_input
            )
            elapsed = time.time() - start_time

            if saved_path:
                downloaded_count += 1
                filename = os.path.basename(saved_path)
                file_size = os.path.getsize(saved_path) / 1024  # KB
                print(f"  \033[32m[✓] {filename} ({file_size:.1f} KB) — {elapsed:.1f}s\033[0m")
                notify(
                    "Certificate Downloaded ✓",
                    f"{filename} ({file_size:.1f} KB)",
                    file_path=saved_path,
                )
            else:
                failed_count += 1
                print(f"  \033[31m[✗] Could not download certificate for NOP ID {user_input} — {elapsed:.1f}s\033[0m")
                notify(
                    "Download Failed",
                    f"Could not find certificate for NOP ID {user_input}.",
                )
        except Exception as e:
            failed_count += 1
            print(f"  \033[31m[ERROR] {e}\033[0m")
            notify(
                "Download Error",
                f"Error: {e}",
            )


if __name__ == "__main__":
    asyncio.run(main())
