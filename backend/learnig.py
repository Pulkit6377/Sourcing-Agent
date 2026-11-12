import asyncio
from playwright.async_api import async_playwright


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )

        page = await browser.new_page()

        await page.goto(
            "https://boodmo.com",
            wait_until="domcontentloaded"
        )

        print("Page title:", await page.title())
        print("Current URL:", page.url)

        await browser.close()


asyncio.run(main())