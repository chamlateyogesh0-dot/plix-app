from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class TrackedProduct(Base):
    __tablename__ = "tracked_products"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    search_query = Column(String)
    target_price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    results = relationship("StoreResult", back_populates="product", cascade="all, delete-orphan")

class StoreResult(Base):
    __tablename__ = "store_results"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("tracked_products.id"))
    platform = Column(String)
    title = Column(String)
    price = Column(Float)
    status = Column(String)
    url = Column(String)
    
    product = relationship("TrackedProduct", back_populates="results")
