from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    """A single line item (product and quantity) within an order."""

    productId: str
    quantity: int


class OrderRequest(BaseModel):
    """Request body for creating or updating an order."""

    items: List[OrderItem]


class OrderStatusUpdate(BaseModel):
    """Request body for changing an order's status."""

    status: str


class OrderInDB(BaseModel):
    """Order document as stored in MongoDB."""

    id: Optional[str] = Field(None, alias="_id")
    items: List[OrderItem]
    total: float = 0.0
    status: str = "pending"
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)


class OrderResponse(BaseModel):
    """Order representation returned by the API."""

    id: str
    items: List[OrderItem]
    total: float
    status: str = "pending"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
