async def _first_product(client):
    body = (await client.get("/api/products", params={"limit": 1})).json()
    return body["data"][0]


async def test_get_product_includes_stock_as_number(client):
    product = await _first_product(client)
    resp = await client.get(f"/api/products/{product['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert "stock" in body
    assert isinstance(body["stock"], (int, float))


async def test_patch_stock_updates_value(client):
    product = await _first_product(client)
    resp = await client.patch(
        f"/api/products/{product['id']}/stock", json={"stock": 75}
    )
    assert resp.status_code == 200
    assert resp.json()["stock"] == 75

    # Confirm persisted via GET.
    after = (await client.get(f"/api/products/{product['id']}")).json()
    assert after["stock"] == 75


async def test_patch_stock_with_negative_returns_400(client):
    product = await _first_product(client)
    resp = await client.patch(
        f"/api/products/{product['id']}/stock", json={"stock": -10}
    )
    assert resp.status_code == 400


async def test_post_order_reduces_product_stock(client):
    product = await _first_product(client)
    original_stock = product["stock"]
    qty = 3

    resp = await client.post(
        "/api/orders",
        json={"items": [{"productId": product["id"], "quantity": qty}]},
    )
    assert resp.status_code in (200, 201)

    after = (await client.get(f"/api/products/{product['id']}")).json()
    assert after["stock"] == original_stock - qty


async def test_post_order_with_insufficient_stock_returns_400(client):
    product = await _first_product(client)
    too_many = product["stock"] + 1

    resp = await client.post(
        "/api/orders",
        json={"items": [{"productId": product["id"], "quantity": too_many}]},
    )
    assert resp.status_code == 400


async def test_stock_unchanged_when_order_rejected(client):
    product = await _first_product(client)
    original_stock = product["stock"]

    resp = await client.post(
        "/api/orders",
        json={"items": [{"productId": product["id"], "quantity": original_stock + 1}]},
    )
    assert resp.status_code == 400

    after = (await client.get(f"/api/products/{product['id']}")).json()
    assert after["stock"] == original_stock


async def test_post_product_sets_stock(client):
    resp = await client.post(
        "/api/products",
        json={
            "name": "Stock Test Item",
            "category": "Electronics",
            "price": 9.99,
            "stock": 42,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["stock"] == 42


async def test_patch_stock_without_auth_returns_401_or_403(unauth_client, client):
    # Get a valid product id via the authenticated client (GET /api/products
    # itself doesn't require auth, but using the same client keeps the test
    # focused on the PATCH auth gate).
    product = await _first_product(client)

    resp = await unauth_client.patch(
        f"/api/products/{product['id']}/stock", json={"stock": 10}
    )
    assert resp.status_code in (401, 403)
