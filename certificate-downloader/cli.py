import asyncio
from downloader import download_certificate


async def main():

    urls = []

    try:
        with open("urls.txt") as f:
            urls = [line.strip() for line in f if line.strip()]
    except:
        print("urls.txt not found")
        return

    if not urls:
        print("No URLs provided")
        return

    for url in urls:
        await download_certificate(url)


asyncio.run(main())