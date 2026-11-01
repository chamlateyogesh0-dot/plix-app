import re
import asyncio
from bs4 import BeautifulSoup
from scraper.base_scraper import BaseScraper

class AmazonScraper(BaseScraper):
    async def scrape(self, url: str):
        max_retries = 3
        retry_delay = 2
        content = None
        title = "Amazon Product Analysis"
        browser = None
        page = None

        # Automatic Retry & Network Error Shield
        for attempt in range(max_retries):
            try:
                page, browser, content, title = await self.get_page_content(url)
                if content:
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    if browser:
                        await browser.close()
                    raise Exception(f"Amazon Network Error after {max_retries} retries: {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))

        try:
            soup = BeautifulSoup(content, 'html.parser')
            product_title = title
            price = 0.0
            product_url = url

            # Extract Title if available from page
            title_elem = soup.find("span", {"id": "productTitle"})
            if title_elem:
                product_title = title_elem.text.strip()

            # Primary Amazon Price Classes
            price_elem = (
                soup.find("span", {"class": "a-price-whole"}) or
                soup.find("span", {"id": "priceblock_ourprice"}) or
                soup.find("span", {"id": "priceblock_dealprice"}) or
                soup.find("span", {"class": "a-offscreen"})
            )
            
            if price_elem:
                price = self.clean_price(price_elem.text)

            # Strict Regex Fallback for Amazon
            if price == 0.0:
                potential_elems = soup.find_all(class_=re.compile("a-price-whole|price|offscreen"))
                for elem in potential_elems:
                    cleaned = self.clean_price(elem.text)
                    if 100 <= cleaned <= 400000:
                        price = cleaned
                        break

            if browser:
                await browser.close()

            return {
                "title": product_title if product_title != title else "Amazon Verified Product",
                "price": price,
                "platform": "Amazon",
                "status": "Available" if price > 0 else "Out of Stock",
                "url": product_url
            }

        except Exception as e:
            if browser:
                await browser.close()
            return {
                "title": "Amazon Parsing Error",
                "price": 0.0,
                "platform": "Amazon",
                "status": "Parsing Failed",
                "url": url
            }
