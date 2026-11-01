from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import shutil
import httpx
from sqlalchemy.orm import Session
from app.scraper.scraper_engine import SmartFetchEngine
from app.database import init_db, get_db
from app.models import TrackedProduct, StoreResult

app = FastAPI(title="Plix - Intelligent Price Tracking")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

templates = Jinja2Templates(directory="templates")
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

engine = SmartFetchEngine()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

async def send_telegram_alert(chat_id: str, message: str):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
            return True
        except Exception:
            return False

# Pydantic Request Model
class ScrapeRequest(BaseModel):
    url: str
    target_price: float = 0.0
    telegram_chat_id: str = ""

GENERIC_CATEGORIES = [
    "mobile", "mobiles", "phone", "phones", "smartphone", "smartphones",
    "shoe", "shoes", "sneaker", "sneakers", "laptop", "laptops",
    "watch", "watches", "smartwatch", "clothes", "tshirt", "jeans"
]

def generate_ai_decision(prices: list) -> dict:
    valid_prices = [p for p in prices if p > 0]
    if not valid_prices:
        return {
            "verdict": "WAIT",
            "badge": "⚠️ Price Data Pending",
            "color": "amber",
            "message": "Prices could not be verified across stores. Try direct product links."
        }
    min_price = min(valid_prices)
    if min_price < 2000:
        return {
            "verdict": "BUY NOW",
            "badge": "🟢 Best Value Deal",
            "color": "emerald",
            "message": f"Lowest price detected at ₹{min_price:,.2f}. Excellent time to buy!"
        }
    else:
        return {
            "verdict": "COMPARE & BUY",
            "badge": "🔵 Multi-Store Active",
            "color": "blue",
            "message": f"Comparing live prices across Amazon, Flipkart, and Meesho. Best available starting at ₹{min_price:,.2f}."
        }

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

# SINGLE, UNIFIED & BULLETPROOF SCRAPE ENDPOINT (Duplicates Removed)
@app.post("/api/scrape")
async def scrape_endpoint(request: ScrapeRequest, db: Session = Depends(get_db)):
    input_text = request.url.strip()
    
    # Generic keyword block check
    if input_text.lower() in GENERIC_CATEGORIES:
        raise HTTPException(
            status_code=400, 
            detail="⚠️ Product name is MUST! Generic categories are not allowed. Please enter a specific model."
        )
    
    try:
        results = await engine.scrape_product(input_text)
        prices = [r.get("price", 0.0) for r in results]
        ai_advice = generate_ai_decision(prices)
        
        # Save to SQLite Database (Watchlist / History)
        db_product = TrackedProduct(search_query=input_text)
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        for r in results:
            db_result = StoreResult(
                product_id=db_product.id,
                platform=r.get("platform", "Unknown"),
                title=r.get("title", input_text),
                price=r.get("price", 0.0),
                status=r.get("status", "Unknown"),
                url=r.get("url", "#")
            )
            db.add(db_result)
        db.commit()

        # Telegram Alert
        if request.telegram_chat_id:
            min_p = min([p for p in prices if p > 0], default=0)
            msg = f"🔔 *Plix Price Alert*\n📦 Product: `{input_text}`\n💰 Best Price: ₹{min_p:,.2f}\n💡 Verdict: *{ai_advice['verdict']}*"
            await send_telegram_alert(request.telegram_chat_id, msg)

        return {
            "success": True,
            "results": results,
            "ai_decision": ai_advice
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.get("/api/watchlist")
async def get_watchlist(db: Session = Depends(get_db)):
    products = db.query(TrackedProduct).order_by(TrackedProduct.created_at.desc()).limit(10).all()
    history = []
    for p in products:
        item_results = [{"platform": r.platform, "price": r.price, "status": r.status, "url": r.url} for r in p.results]
        history.append({
            "id": p.id,
            "query": p.search_query,
            "timestamp": p.created_at.strftime("%Y-%m-%d %H:%M"),
            "results": item_results
        })
    return {"success": True, "watchlist": history}

@app.post("/api/upload-image")
async def upload_image_endpoint(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed!")
    file_path = f"static/uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"success": True, "url": f"/{file_path}"}

@app.delete("/api/watchlist/{product_id}")
async def delete_watchlist_item(product_id: int, db: Session = Depends(get_db)):
    product = db.query(TrackedProduct).filter(TrackedProduct.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(product)
    db.commit()
    return {"success": True, "message": "Item deleted from watchlist"}
@app.delete("/api/watchlist/{item_id}")
def delete_watchlist_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TrackedProduct).filter(TrackedProduct.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"success": True, "message": "Deleted successfully"}
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

# 1. Feedback Database Model (Appends to local SQLite)
class FeedbackModel(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer, default=5)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class FeedbackRequest(BaseModel):
    rating: int
    message: str

# 2. API Endpoint to Receive and Save Feedback Locally
@app.post("/api/feedback")
async def save_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    try:
        new_feedback = FeedbackModel(rating=data.rating, message=data.message)
        db.add(new_feedback)
        db.commit()
        return {"success": True, "message": "Feedback saved locally on computer!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))