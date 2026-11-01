
import re
import asyncio
from bs4 import BeautifulSoup
from scraper.base_scraper import BaseScraper

class FlipkartScraper(BaseScraper):
    async def scrape(self, url: str):
        max_retries = 3
        retry_delay = 2
        content = None
        title = "Product Analysis"
        browser = None
        page = None

        # Layer 1: Automatic Retry & Network Error Shield
        for attempt in range(max_retries):
            try:
                page, browser, content, title = await self.get_page_content(url)
                if content:
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    if browser:
                        await browser.close()
                    raise Exception(f"Network/Browser Error after {max_retries} retries: {str(e)}")
                await asyncio.sleep(retry_delay * (attempt + 1))

        try:
            soup = BeautifulSoup(content, 'html.parser')
            product_title = title
            price = 0.0
            product_url = url

            # Layer 2: Precise Search & Product Card Extraction
            if "/search?" in url or "q=" in url:
                result_item = soup.select_one("div._75nlfW") or soup.select_one("div.slAVV4") or soup.select_one("div._1AtVbE")
                if result_item:
                    title_elem = result_item.select_one("a.wjcEIp") or result_item.select_one("a.s1Q9rs") or result_item.select_one("a._2mylT6")
                    price_elem = result_item.select_one("div.Nx9bqj") or result_item.select_one("div._30jeq3")
                    link_elem = result_item.select_one("a._2rpwq9") or result_item.select_one("a.s1Q9rs") or result_item.select_one("a")
                    
                    product_title = title_elem.text.strip() if title_elem else title
                    if price_elem:
                        price = self.clean_price(price_elem.text)
                    
                    href = link_elem.get('href') if link_elem else ""
                    product_url = "https://www.flipkart.com" + href if href.startswith("/") else (href if href else url)

            # Layer 3: Multi-Class Direct Price Extraction
            if price == 0.0:
                price_elem = (
                    soup.find("div", {"class": "Nx9bqj CxhGGd"}) or 
                    soup.find("div", {"class": "Nx9bqj"}) or
                    soup.find("div", {"class": "_30jeq3 _16Jk6d"}) or 
                    soup.find("div", {"class": "_30jeq3"})
                )
                if price_elem:
                    price = self.clean_price(price_elem.text)

            # Layer 4: Intelligent Strict Regex Fallback (Filters out Banners & EMIs)
            if price == 0.0:
                potential_price_elems = soup.find_all(class_=re.compile("Nx9bqj|_30jeq3"))
                for elem in potential_price_elems:
                    cleaned = self.clean_price(elem.text)
                    if 100 <= cleaned <= 300000:  # Valid realistic product price range
                        price = cleaned
                        break

            if browser:
                await browser.close()
            
            return {
                "title": product_title if product_title != title else "Plix Verified Product",
                "price": price,
                "platform": "Flipkart",
                "status": "Available" if price > 0 else "Out of Stock",
                "url": product_url
            }

        except Exception as e:
            if browser:
                await browser.close()
            # Graceful fallback instead of crashing the whole thread
            return {
                "title": "Parsing Error / Limited Data",
                "price": 0.0,
                "platform": "Flipkart",
                "status": "Parsing Failed",
                "url": url
            }
