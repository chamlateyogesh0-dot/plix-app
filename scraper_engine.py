import urllib.parse
import asyncio
from amazon_scraper import AmazonScraper
from flipkart_scraper import FlipkartScraper
from meesho_scraper import MeeshoScraper

class SmartFetchEngine:
    def __init__(self):
        self.amazon = AmazonScraper()
        self.flipkart = FlipkartScraper()
        self.meesho = MeeshoScraper()

    def _resolve_urls(self, query: str):
        query = query.strip()
        if query.startswith("http://") or query.startswith("https://"):
            return {
                "amazon": query if "amazon" in query else f"https://www.amazon.in/s?k={urllib.parse.quote(query)}",
                "flipkart": query if "flipkart" in query else f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}",
                "meesho": query if "meesho" in query else f"https://www.meesho.com/search?q={urllib.parse.quote(query)}"
            }
        
        encoded_query = urllib.parse.quote(query)
        return {
            "amazon": f"https://www.amazon.in/s?k={encoded_query}",
            "flipkart": f"https://www.flipkart.com/search?q={encoded_query}",
            "meesho": f"https://www.meesho.com/search?q={encoded_query}"
        }

    async def scrape_product(self, query: str):
        urls = self._resolve_urls(query)
        
        targets = [
            ("Amazon", self.amazon, urls["amazon"]),
            ("Flipkart", self.flipkart, urls["flipkart"]),
            ("Meesho", self.meesho, urls["meesho"])
        ]

        results = []

        for platform_name, scraper_obj, target_url in targets:
            res = None
            
            # Pehli koshish (First Attempt)
            try:
                res = await scraper_obj.scrape(target_url)
            except Exception:
                res = None

            # Agar pehli baar me fail ho gaya ya price 0.0 aaya, toh SIRF USI platform ko retry karo
            if not res or res.get("price", 0.0) == 0.0:
                print(f"⚠️ {platform_name} scraping failed/0.0. Retrying specifically for {platform_name}...")
                try:
                    await asyncio.sleep(1.5)  # Anti-bot bypass ke liye chhota sa natural gap
                    res = await scraper_obj.scrape(target_url)
                except Exception:
                    res = None

            # Final validation check after retry
            if not res or res.get("price", 0.0) == 0.0:
                results.append({
                    "title": f"{platform_name} Search Result ({query})",
                    "price": 0.0,
                    "platform": platform_name,
                    "status": "Out of Stock / Blocked",
                    "url": target_url
                })
            else:
                results.append(res)

        return results
