from collections import defaultdict
from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from database import orders_collection, products_collection
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _parse_date(value: str) -> Optional[datetime]:
    # Accept either a plain date (YYYY-MM-DD) or full ISO timestamp.
    try:
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


@router.get("/sales")
async def sales_analytics(
    _current_user: dict = Depends(get_current_user),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
):
    query: dict = {}
    if startDate or endDate:
        created_filter: dict = {}
        if startDate:
            start = _parse_date(startDate)
            if start is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Invalid startDate"},
                )
            created_filter["$gte"] = start
        if endDate:
            end = _parse_date(endDate)
            if end is None:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Invalid endDate"},
                )
            created_filter["$lte"] = end
        query["createdAt"] = created_filter

    total_revenue = 0.0
    total_orders = 0
    product_totals: dict[str, dict] = defaultdict(lambda: {"totalQuantity": 0, "totalRevenue": 0.0})
    revenue_by_day: dict[str, float] = defaultdict(float)

    product_cache: dict[str, dict] = {}

    cursor = orders_collection.find(query)
    async for order in cursor:
        order_total = float(order.get("total") or 0)
        total_revenue += order_total
        total_orders += 1

        created_at = order.get("createdAt")
        if isinstance(created_at, datetime):
            revenue_by_day[created_at.strftime("%Y-%m-%d")] += order_total

        for item in order.get("items", []):
            product_id_raw = item.get("productId")
            quantity = item.get("quantity") or 0
            if not product_id_raw:
                continue
            product_id = str(product_id_raw)

            if product_id not in product_cache and ObjectId.is_valid(product_id):
                product_cache[product_id] = await products_collection.find_one(
                    {"_id": ObjectId(product_id)}
                ) or {}
            product = product_cache.get(product_id, {})
            price = float(product.get("price") or 0)

            agg = product_totals[product_id]
            agg["totalQuantity"] += quantity
            agg["totalRevenue"] += price * quantity
            agg["name"] = product.get("name")

    top_products = [
        {
            "productId": pid,
            "name": data.get("name"),
            "totalQuantity": data["totalQuantity"],
            "totalRevenue": round(data["totalRevenue"], 2),
        }
        for pid, data in product_totals.items()
    ]
    top_products.sort(key=lambda p: p["totalQuantity"], reverse=True)
    top_products = top_products[:5]

    revenue_by_period = [
        {"period": day, "revenue": round(revenue, 2)}
        for day, revenue in sorted(revenue_by_day.items())
    ]

    return {
        "totalRevenue": round(total_revenue, 2),
        "totalOrders": total_orders,
        "topProducts": top_products,
        "revenueByPeriod": revenue_by_period,
    }
