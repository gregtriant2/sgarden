from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from routes import products as products_module
from security.jwt_handler import get_current_user


SEED_PRODUCTS = [
    {"name": "Wireless Mouse", "description": "Ergonomic wireless mouse with USB receiver", "category": "Electronics", "price": 29.99, "stock": 150},
    {"name": "Mechanical Keyboard", "description": "RGB mechanical keyboard with Cherry MX switches", "category": "Electronics", "price": 89.99, "stock": 75},
    {"name": "USB-C Hub", "description": "7-in-1 USB-C hub with HDMI and Ethernet", "category": "Electronics", "price": 45.99, "stock": 200},
    {"name": "Monitor Stand", "description": "Adjustable monitor stand with USB ports", "category": "Accessories", "price": 34.99, "stock": 120},
    {"name": "Webcam HD", "description": "1080p HD webcam with built-in microphone", "category": "Electronics", "price": 59.99, "stock": 90},
    {"name": "Desk Lamp", "description": "LED desk lamp with adjustable brightness", "category": "Accessories", "price": 24.99, "stock": 180},
    {"name": "Cable Organizer", "description": "Silicone cable management clips, pack of 10", "category": "Accessories", "price": 9.99, "stock": 500},
    {"name": "Laptop Sleeve", "description": "Neoprene laptop sleeve for 15-inch laptops", "category": "Accessories", "price": 19.99, "stock": 250},
    {"name": "External SSD", "description": "1TB portable external SSD, USB 3.2", "category": "Storage", "price": 79.99, "stock": 60},
    {"name": "USB Flash Drive", "description": "64GB USB 3.0 flash drive", "category": "Storage", "price": 12.99, "stock": 400},
    {"name": "Ethernet Cable", "description": "Cat6 ethernet cable, 10 meters", "category": "Networking", "price": 8.99, "stock": 300},
    {"name": "Wi-Fi Router", "description": "Dual-band Wi-Fi 6 router", "category": "Networking", "price": 129.99, "stock": 45},
    {"name": "Mouse Pad XL", "description": "Extended gaming mouse pad, 900x400mm", "category": "Accessories", "price": 15.99, "stock": 200},
    {"name": "Headphone Stand", "description": "Aluminum headphone stand", "category": "Accessories", "price": 22.99, "stock": 100},
    {"name": "Power Strip", "description": "6-outlet power strip with USB charging", "category": "Electronics", "price": 18.99, "stock": 350},
]


@pytest.fixture
def seed_products():
    return SEED_PRODUCTS


@pytest_asyncio.fixture
async def client():
    mock_client = AsyncMongoMockClient()
    mock_db = mock_client["sgarden_test"]
    fake_products = mock_db["products"]

    now = datetime.utcnow()
    await fake_products.insert_many(
        [{**p, "createdAt": now, "updatedAt": now} for p in SEED_PRODUCTS]
    )

    original = products_module.products_collection
    products_module.products_collection = fake_products

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: {"_id": "test-user", "username": "tester", "role": "admin"}
    app.include_router(products_module.router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    products_module.products_collection = original
