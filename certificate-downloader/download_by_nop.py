import asyncio
import os
import sys
import time
from winotify import Notification, audio

# Fix imports so this works from any directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from downloader import NopDownloader


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
    print("\033[36m" + "    ╩ ╩╩═╝╩═╝╩ ╩   ─  Web Scraping Tool v4.0" + "\033[0m")
    print("\033[36m" + "=" * 60 + "\033[0m")


async def main():
    output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_folder, exist_ok=True)

    downloaded_count = 0
    failed_count = 0

    print_banner()
    print(f"\033[33m  Downloads folder: {os.path.abspath(output_folder)}\033[0m")

    # Start persistent browser ONCE
    dl = NopDownloader()
    await dl.start()

    print("\033[90m  Type a NOP ID to download, or S to stop.\033[0m")
    print("\033[36m" + "-" * 60 + "\033[0m")

    try:
        while True:
            print()
            user_input = input("\033[1m  Enter NOP ID (or S to stop): \033[0m").strip()

            if user_input.upper() == "S":
                break

            if not user_input:
                print("  \033[31m[!] NOP ID cannot be empty.\033[0m")
                continue

            start_time = time.time()

            # Step 1: Search
            print("  \033[90m[1/2] Searching USDA database...\033[0m")
            cert_url = await dl.search_nop_id(user_input)

            if not cert_url:
                failed_count += 1
                elapsed = time.time() - start_time
                print(f"  \033[31m[✗] NOP ID {user_input} not found — {elapsed:.1f}s\033[0m")
                notify("NOP ID Not Found", f"NOP ID {user_input} not in USDA database.")
                continue

            # Step 2: Download
            print(f"  \033[90m[2/2] Downloading certificate...\033[0m")
            try:
                saved_path = await dl.download_certificate(cert_url, output_folder, user_input)
                elapsed = time.time() - start_time

                if saved_path:
                    downloaded_count += 1
                    filename = os.path.basename(saved_path)
                    file_size = os.path.getsize(saved_path) / 1024
                    print(f"  \033[32m[✓] {filename} ({file_size:.1f} KB) — {elapsed:.1f}s\033[0m")
                    notify("Certificate Downloaded ✓", f"{filename} ({file_size:.1f} KB)", file_path=saved_path)
                else:
                    failed_count += 1
                    print(f"  \033[31m[✗] Download failed for {user_input} — {elapsed:.1f}s\033[0m")
                    notify("Download Failed", f"Could not download certificate for NOP ID {user_input}.")
            except Exception as e:
                failed_count += 1
                print(f"  \033[31m[ERROR] {e}\033[0m")
    finally:
        print()
        print("\033[36m" + "-" * 60 + "\033[0m")
        print(f"\033[32m  ✓ Downloaded: {downloaded_count} certificate(s)\033[0m")
        if failed_count:
            print(f"\033[31m  ✗ Failed: {failed_count}\033[0m")
        print(f"\033[33m  Saved to: {os.path.abspath(output_folder)}\033[0m")
        print("\033[36m" + "=" * 60 + "\033[0m")
        await dl.stop()


if __name__ == "__main__":
    asyncio.run(main())
