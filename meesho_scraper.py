
import re
import asyncio
from bs4 import BeautifulSoup
from app.scraper.base_scraper import BaseScraper

class MeeshoScraper(BaseScraper):
    async def scrape(self, url: str):
        max_retries = 3
        retry_delay = 2
        content = None
        title = "Meesho Product Analysis"
        browser = None
        page = None

        # Automatic Retry Shield
        for attempt in range(max_retries):
            try:
                page, browser, content, title = await self.get_page_content(url)
                if content:
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    if browser:
                        await browser.close()
                    raise Exception(f"Meesho Network Error after {max_retries} retries: {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))

        try:
            soup = BeautifulSoup(content, 'html.parser')
            product_title = title
            price = 0.0
            product_url = url

            # Extract Title
            title_elem = soup.find("h1", class_=re.compile("ProductTitle|sc-")) or soup.find("span", class_=re.compile("Title"))
            if title_elem:
                product_title = title_elem.text.strip()

            # Meesho Price Classes / Containers
            price_elem = (
                soup.find("span", class_=re.compile("pdp-price|Price")) or
                soup.find("h4", class_=re.compile("price"))
            )

            if price_elem:
                price = self.clean_price(price_elem.text)

            # Strict Regex Fallback for Meesho
            if price == 0.0:
                text_content = soup.get_text()
                matches = re.findall(r'[₹|Rs\.?]\s*([0-9,]+(?:\.[0-9]+)?)', text_content)
                for m in matches:
                    cleaned = self.clean_price(m)
                    if 50 <= cleaned <= 50000:  # Meesho items are usually budget-friendly
                        price = cleaned
                        break

            if browser:
                await browser.close()

            return {
                "title": product_title if product_title != title else "Meesho Verified Product",
                "price": price,
                "platform": "Meesho",
                "status": "Available" if price > 0 else "Out of Stock",
                "url": product_url
            }

        except Exception as e:
            if browser:
                await browser.close()
            return {
                "title": "Meesho Parsing Error",
                "price": 0.0,
                "platform": "Meesho",
                "status": "Parsing Failed",
                "url": url
            }