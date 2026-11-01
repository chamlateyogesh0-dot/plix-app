from pydantic import BaseModel, HttpUrl

class ProductCreate(BaseModel):
    url: str
    target_price: float = None