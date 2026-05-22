from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    productId: str
    quantity: int


class OrderRequest(BaseModel):
    items: List[OrderItem]


class OrderStatusUpdate(BaseModel):
    status: str


class OrderInDB(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    items: List[OrderItem]
    total: float = 0.0
    status: str = "pending"
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)


class OrderResponse(BaseModel):
    id: str
    items: List[OrderItem]
    total: float
    status: str = "pending"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
