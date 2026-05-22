NON_EXISTENT_ID = "000000000000000000000000"


async def _first_product(client):
    body = (await client.get("/api/products", params={"limit": 1})).json()
    return body["data"][0]


async def _create_order(client, product_id: str, quantity: int = 2):
    return await client.post(
        "/api/orders",
        json={"items": [{"productId": product_id, "quantity": quantity}]},
    )


async def test_post_order_returns_with_id_and_items(client):
    product = await _first_product(client)
    resp = await _create_order(client, product["id"], quantity=2)
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert "id" in body and body["id"]
    assert isinstance(body["items"], list)
    assert len(body["items"]) == 1
    assert body["items"][0]["productId"] == product["id"]
    assert body["items"][0]["quantity"] == 2


async def test_order_total_equals_price_times_quantity(client):
    product = await _first_product(client)
    resp = await _create_order(client, product["id"], quantity=3)
    assert resp.json()["total"] == product["price"] * 3


async def test_list_orders_returns_array(client):
    product = await _first_product(client)
    await _create_order(client, product["id"], quantity=1)

    resp = await client.get("/api/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1


async def test_get_single_order_returns_matching_order(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=2)).json()

    resp = await client.get(f"/api/orders/{created['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == created["id"]
    assert body["items"][0]["productId"] == product["id"]
    assert body["items"][0]["quantity"] == 2
    assert body["total"] == product["price"] * 2


async def test_put_order_recalculates_total(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()

    resp = await client.put(
        f"/api/orders/{created['id']}",
        json={"items": [{"productId": product["id"], "quantity": 5}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["quantity"] == 5
    assert body["total"] == product["price"] * 5


async def test_delete_order_returns_200_then_get_returns_404(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()

    del_resp = await client.delete(f"/api/orders/{created['id']}")
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/orders/{created['id']}")
    assert get_resp.status_code == 404


async def test_get_non_existent_order_returns_404(client):
    resp = await client.get(f"/api/orders/{NON_EXISTENT_ID}")
    assert resp.status_code == 404


async def test_post_order_without_auth_returns_401_or_403(unauth_client):
    resp = await unauth_client.post(
        "/api/orders",
        json={"items": [{"productId": NON_EXISTENT_ID, "quantity": 1}]},
    )
    assert resp.status_code in (401, 403)


async def test_new_order_defaults_to_pending(client):
    product = await _first_product(client)
    body = (await _create_order(client, product["id"], quantity=1)).json()
    assert body["status"] == "pending"


async def test_patch_status_pending_to_confirmed(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()

    resp = await client.patch(
        f"/api/orders/{created['id']}/status",
        json={"status": "confirmed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


async def test_full_workflow_pending_to_delivered(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()
    order_id = created["id"]

    for next_status in ("confirmed", "shipped", "delivered"):
        resp = await client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": next_status},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == next_status


async def test_skip_step_returns_400(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()

    resp = await client.patch(
        f"/api/orders/{created['id']}/status",
        json={"status": "shipped"},
    )
    assert resp.status_code == 400


async def test_cancel_pending_order_returns_200(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()

    resp = await client.patch(
        f"/api/orders/{created['id']}/status",
        json={"status": "cancelled"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_delivered_order_cannot_change_status(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()
    order_id = created["id"]

    for next_status in ("confirmed", "shipped", "delivered"):
        await client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": next_status},
        )

    resp = await client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "cancelled"},
    )
    assert resp.status_code == 400


async def test_cancel_shipped_order_returns_400(client):
    product = await _first_product(client)
    created = (await _create_order(client, product["id"], quantity=1)).json()
    order_id = created["id"]

    for next_status in ("confirmed", "shipped"):
        await client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": next_status},
        )

    resp = await client.patch(
        f"/api/orders/{order_id}/status",
        json={"status": "cancelled"},
    )
    assert resp.status_code == 400


async def test_list_orders_filtered_by_status(client):
    product = await _first_product(client)
    pending_order = (await _create_order(client, product["id"], quantity=1)).json()
    confirmed_order = (await _create_order(client, product["id"], quantity=1)).json()

    await client.patch(
        f"/api/orders/{confirmed_order['id']}/status",
        json={"status": "confirmed"},
    )

    resp = await client.get("/api/orders", params={"status": "pending"})
    assert resp.status_code == 200
    body = resp.json()
    assert all(o["status"] == "pending" for o in body)
    ids = {o["id"] for o in body}
    assert pending_order["id"] in ids
    assert confirmed_order["id"] not in ids
