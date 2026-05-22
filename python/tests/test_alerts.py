async def _first_product(client):
    body = (await client.get("/api/products", params={"limit": 1})).json()
    return body["data"][0]


async def test_get_alerts_returns_200_with_array(client):
    resp = await client.get("/api/alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_products_below_threshold_appear_in_alerts(client):
    # Seed minimum stock is 45 (Wi-Fi Router), so threshold=50 puts at least
    # one product below threshold.
    await client.put("/api/alerts/threshold", json={"threshold": 50})

    alerts = (await client.get("/api/alerts")).json()
    names = [a["name"] for a in alerts]
    assert "Wi-Fi Router" in names  # stock 45 < 50


async def test_put_threshold_returns_200_with_value(client):
    resp = await client.put("/api/alerts/threshold", json={"threshold": 25})
    assert resp.status_code == 200
    assert resp.json()["threshold"] == 25


async def test_each_alert_has_severity_in_allowed_set(client):
    # Force at least one alert by dropping a product to stock 1.
    product = await _first_product(client)
    await client.patch(f"/api/products/{product['id']}/stock", json={"stock": 1})

    alerts = (await client.get("/api/alerts")).json()
    assert len(alerts) > 0
    for alert in alerts:
        assert alert["severity"] in ("critical", "warning", "info")


async def test_products_above_threshold_are_excluded(client):
    await client.put("/api/alerts/threshold", json={"threshold": 50})

    alerts = (await client.get("/api/alerts")).json()
    names = {a["name"] for a in alerts}
    # Cable Organizer has stock 500, well above the threshold.
    assert "Cable Organizer" not in names
    # And every reported alert must have stock < threshold.
    for alert in alerts:
        assert alert["stock"] < 50


async def test_each_alert_includes_product_name_and_stock(client):
    product = await _first_product(client)
    await client.patch(f"/api/products/{product['id']}/stock", json={"stock": 1})

    alerts = (await client.get("/api/alerts")).json()
    assert len(alerts) > 0
    for alert in alerts:
        assert isinstance(alert["name"], str) and alert["name"]
        assert isinstance(alert["stock"], (int, float))


async def test_get_alerts_without_auth_returns_401_or_403(unauth_client):
    resp = await unauth_client.get("/api/alerts")
    assert resp.status_code in (401, 403)
