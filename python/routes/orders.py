from datetime import datetime
from typing import Iterable

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from database import orders_collection, products_collection
from models.order import OrderItem, OrderRequest
from security.jwt_handler import get_current_user

router = APIRouter(prefix="/api/orders", tags=["orders"])


async def _calculate_total(items: Iterable[OrderItem]) -> float:
    total = 0.0
    for item in items:
        if not ObjectId.is_valid(item.productId):
            continue
        product = await products_collection.find_one({"_id": ObjectId(item.productId)})
        if product and isinstance(product.get("price"), (int, float)):
            total += float(product["price"]) * item.quantity
    return total


def _order_to_response(order: dict) -> dict:
    return {
        "id": str(order["_id"]),
        "items": [
            {"productId": str(item.get("productId")), "quantity": item.get("quantity")}
            for item in order.get("items", [])
        ],
        "total": order.get("total", 0),
        "createdAt": order["createdAt"].isoformat() if order.get("createdAt") else None,
        "updatedAt": order["updatedAt"].isoformat() if order.get("updatedAt") else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(request: OrderRequest, current_user: dict = Depends(get_current_user)):
    # Aggregate quantities by productId so duplicate items in a single order
    # don't bypass the per-product stock check.
    needed: dict[str, int] = {}
    for item in request.items:
        if not ObjectId.is_valid(item.productId):
            continue
        needed[item.productId] = needed.get(item.productId, 0) + item.quantity

    insufficient: dict[str, str] = {}
    next_stock: dict[str, int] = {}
    for product_id_str, qty in needed.items():
        product = await products_collection.find_one({"_id": ObjectId(product_id_str)})
        if product is None:
            continue
        available = product.get("stock") or 0
        if available < qty:
            insufficient[product_id_str] = (
                f"Requested {qty} but only {available} in stock"
            )
        else:
            next_stock[product_id_str] = available - qty

    if insufficient:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Insufficient stock", "errors": insufficient},
        )

    now = datetime.utcnow()
    for product_id_str, new_stock in next_stock.items():
        await products_collection.update_one(
            {"_id": ObjectId(product_id_str)},
            {"$set": {"stock": new_stock, "updatedAt": now}},
        )

    order_doc = {
        "items": [item.model_dump() for item in request.items],
        "total": await _calculate_total(request.items),
        "createdAt": now,
        "updatedAt": now,
    }
    result = await orders_collection.insert_one(order_doc)
    order_doc["_id"] = result.inserted_id
    return _order_to_response(order_doc)


@router.get("")
async def list_orders(current_user: dict = Depends(get_current_user)):
    orders = []
    cursor = orders_collection.find()
    async for order in cursor:
        orders.append(_order_to_response(order))
    return orders


@router.get("/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return _order_to_response(order)


@router.put("/{order_id}")
async def update_order(order_id: str, request: OrderRequest, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {
            "items": [item.model_dump() for item in request.items],
            "total": await _calculate_total(request.items),
            "updatedAt": datetime.utcnow(),
        }},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    order = await orders_collection.find_one({"_id": ObjectId(order_id)})
    return _order_to_response(order)


@router.delete("/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(order_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await orders_collection.delete_one({"_id": ObjectId(order_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    return {"message": "Order deleted"}
