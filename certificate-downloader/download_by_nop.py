import asyncio
import os
import sys
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


async def main():
    # Downloads go to the device's default Downloads folder
    output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(output_folder, exist_ok=True)

    base_url: str = "https://organic.ams.usda.gov/integrity/CP/OPP?cid=87&nopid="
    downloaded_count: int = 0

    print("=" * 55)
    print("   USDA NOP Certificate Downloader (Web Scraping)")
    print("=" * 55)
    print(f"  Certificates will be saved to: {os.path.abspath(output_folder)}")
    print("-" * 55)

    while True:
        print()
        user_input: str = input("Enter NOP ID (or S to stop): ").strip()

        # Stop condition
        if user_input.upper() == "S":
            print()
            print("-" * 55)
            print(f"  Done! {downloaded_count} certificate(s) downloaded.")
            print("=" * 55)
            break

        # Validate input
        if not user_input:
            print("  [!] NOP ID cannot be empty. Try again.")
            continue

        # Build URL
        full_url: str = f"{base_url}{user_input}"
        print(f"  Searching for NOP ID: {user_input} ...")

        # --- Step 1: Open certificate page in external browser immediately ---
        print(f"  [>>] Opening in browser: {full_url}")
        webbrowser.open(full_url)

        # --- Step 2: Download the certificate via Playwright (at the same time) ---
        try:
            saved_path = await download_certificate(full_url, output_folder=output_folder)
            if saved_path:
                downloaded_count += 1
                filename = os.path.basename(saved_path)
                print(f"  [OK] {filename} saved!")
                notify(
                    "Certificate Downloaded",
                    filename,
                    file_path=saved_path,
                )
            else:
                print(f"  [!] Could not download certificate for NOP ID {user_input}.")
                notify(
                    "Download Failed",
                    f"Could not find certificate for NOP ID {user_input}.",
                )
        except Exception as e:
            print(f"  [ERROR] Failed to download certificate for NOP ID {user_input}")
            print(f"          {e}")
            notify(
                "Download Error",
                f"Error downloading NOP ID {user_input}: {e}",
            )


if __name__ == "__main__":
    asyncio.run(main())
