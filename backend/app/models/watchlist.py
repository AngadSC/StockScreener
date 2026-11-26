from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.models.stock import StockDetail

class WatchlistItemCreate(BaseModel):
    ticker: str

class WatchlistItemResponse(BaseModel):
    id: int
    ticker: str
    added_at: datetime
    stock: Optional[StockDetail] = None

    model_config = ConfigDict(from_attributes=True)

class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    total: int
