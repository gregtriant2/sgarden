async def _first_product(client):
    body = (await client.get("/api/products", params={"limit": 1})).json()
    return body["data"][0]


async def _seed_orders(client):
    products = (await client.get("/api/products", params={"limit": 3})).json()["data"]
    for product in products:
        await client.post(
            "/api/orders",
            json={"items": [{"productId": product["id"], "quantity": 2}]},
        )
    return products


async def test_sales_analytics_returns_200_with_object(client):
    await _seed_orders(client)
    resp = await client.get("/api/analytics/sales")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert "totalRevenue" in body
    assert "totalOrders" in body
    assert "topProducts" in body
    assert "revenueByPeriod" in body


async def test_total_revenue_is_positive_number(client):
    await _seed_orders(client)
    body = (await client.get("/api/analytics/sales")).json()
    assert isinstance(body["totalRevenue"], (int, float))
    assert body["totalRevenue"] > 0


async def test_total_orders_is_positive_number(client):
    await _seed_orders(client)
    body = (await client.get("/api/analytics/sales")).json()
    assert isinstance(body["totalOrders"], int)
    assert body["totalOrders"] > 0


async def test_top_products_have_required_fields(client):
    await _seed_orders(client)
    body = (await client.get("/api/analytics/sales")).json()
    assert isinstance(body["topProducts"], list)
    assert len(body["topProducts"]) > 0
    for entry in body["topProducts"]:
        assert "productId" in entry
        assert "name" in entry
        assert "totalQuantity" in entry
        assert "totalRevenue" in entry


async def test_revenue_by_period_is_array_or_object(client):
    await _seed_orders(client)
    body = (await client.get("/api/analytics/sales")).json()
    assert isinstance(body["revenueByPeriod"], (list, dict))


async def test_date_range_filter_returns_200(client):
    await _seed_orders(client)
    resp = await client.get(
        "/api/analytics/sales",
        params={"startDate": "2024-01-01", "endDate": "2099-12-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "totalRevenue" in body


async def test_future_date_range_returns_zero_revenue_and_orders(client):
    await _seed_orders(client)
    resp = await client.get(
        "/api/analytics/sales",
        params={"startDate": "2099-01-01", "endDate": "2099-12-31"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalRevenue"] == 0
    assert body["totalOrders"] == 0


async def test_sales_analytics_without_auth_returns_401_or_403(unauth_client):
    resp = await unauth_client.get("/api/analytics/sales")
    assert resp.status_code in (401, 403)
