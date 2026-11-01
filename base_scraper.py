
from playwright.async_api import async_playwright
import re
import json

class BaseScraper:
    async def get_page_content(self, url: str):
        p = await async_playwright().start()
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )
        
        page = await context.new_page()
        
        # Anti-detection JS injection
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            # 4 seconds wait for search results / dynamic elements to load fully
            await page.wait_for_timeout(4000)
            
            content = await page.content()
            title = await page.title()
            
            return page, browser, content, title
            
        except Exception as e:
            await browser.close()
            raise e

    def clean_price(self, price_str: str) -> float:
        try:
            cleaned = re.sub(r'[^\d.]', '', price_str)
            return float(cleaned) if cleaned else 0.0
        except Exception:
            return 0.0

    def extract_from_json_ld(self, soup):
        """Extracts product title and price directly from hidden SEO JSON-LD tags"""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        item = next((d for d in data if d.get('@type') == 'Product'), None)
                    else:
                        item = data if data.get('@type') == 'Product' else None
                        
                    if item:
                        name = item.get('name', '')
                        offers = item.get('offers', {})
                        if isinstance(offers, list):
                            offers = offers[0]
                        price = float(offers.get('price', 0.0))
                        if price > 0:
                            return name, price
        except Exception:
            pass
        return None, 0.0