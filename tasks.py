from celery_app import celery_app
from scraper_engine import SmartFetchEngine
import asyncio
import os
import httpx

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

async def send_branded_telegram_alert(chat_id: str, product: str, price: float):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    
    logo_url = "https://i.imgur.com/3Z6bZ7t.png" # Plix official brand logo placeholder
    caption = (
        f"🤖 *Plix Neural Price Alert* (App ID: `PLIX-PROD-01`)\n\n"
        f"📦 *Product:* `{product}`\n"
        f"💰 *Current Drop Price:* ₹{price:,.2f}\n"
        f"🎯 *Status:* Target matched! Buy now."
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={
                "chat_id": chat_id,
                "photo": logo_url,
                "caption": caption,
                "parse_mode": "Markdown"
            })
        except Exception:
            pass

@celery_app.task(bind=True)
def run_background_scrape(self, query: str, target_price: float, chat_id: str):
    engine = SmartFetchEngine()
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(engine.scrape_product(query))
    
    valid_prices = [r.get("price", 0.0) for r in results if r.get("price", 0.0) > 0]
    if valid_prices:
        best_price = min(valid_prices)
        # Check target price condition for Telegram alert
        if target_price > 0 and best_price <= target_price:
            loop.run_until_complete(send_branded_telegram_alert(chat_id, query, best_price))
            
    return {"status": "Completed", "results": results}
