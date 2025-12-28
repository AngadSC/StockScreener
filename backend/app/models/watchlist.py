from pydantic import BaseModel
from datetime import datetime
from typing import List
from .stock import StockDetail

class WatchlistItemBase(BaseModel):
    ticker: str

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemResponse(WatchlistItemBase):
    id: int
    added_at: datetime
    stock: StockDetail  # Nested stock data
    
    class Config:
        from_attributes = True

class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    total: int
