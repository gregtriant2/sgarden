from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import products_collection, settings_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

DEFAULT_THRESHOLD = 20
SETTINGS_DOC_ID = "alerts"


class ThresholdRequest(BaseModel):
    threshold: int


async def _current_threshold() -> int:
    doc = await settings_collection.find_one({"_id": SETTINGS_DOC_ID})
    if doc and isinstance(doc.get("threshold"), (int, float)):
        return int(doc["threshold"])
    return DEFAULT_THRESHOLD


def _severity(stock: int, threshold: int) -> str:
    # critical: ≤25% of threshold, warning: ≤50%, info: anything else below.
    if stock <= threshold / 4:
        return "critical"
    if stock <= threshold / 2:
        return "warning"
    return "info"


@router.get("")
async def list_alerts(current_user: dict = Depends(get_current_user)):
    threshold = await _current_threshold()
    alerts = []
    cursor = products_collection.find({"stock": {"$lt": threshold}})
    async for product in cursor:
        stock = product.get("stock") or 0
        alerts.append({
            "productId": str(product["_id"]),
            "name": product.get("name"),
            "stock": stock,
            "severity": _severity(stock, threshold),
        })
    return alerts


@router.put("/threshold")
async def set_threshold(
    request: ThresholdRequest,
    current_user: dict = Depends(get_current_user),
):
    if request.threshold < 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Validation failed", "errors": {"threshold": "Threshold must be non-negative"}},
        )

    await settings_collection.update_one(
        {"_id": SETTINGS_DOC_ID},
        {"$set": {"threshold": request.threshold}},
        upsert=True,
    )
    return {"threshold": request.threshold}
