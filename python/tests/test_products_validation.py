NON_EXISTENT_ID = "000000000000000000000000"


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "Test Product",
        "description": "A test product",
        "category": "Electronics",
        "price": 9.99,
        "stock": 1,
    }
    payload.update(overrides)
    return payload


async def test_post_missing_name_returns_400_with_errors_name(client):
    payload = _valid_payload()
    payload.pop("name")
    resp = await client.post("/api/products", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert "name" in body["errors"]
    assert isinstance(body["errors"]["name"], str)


async def test_post_negative_price_returns_400_with_errors_price(client):
    resp = await client.post("/api/products", json=_valid_payload(price=-5))
    assert resp.status_code == 400
    body = resp.json()
    assert "price" in body["errors"]
    assert isinstance(body["errors"]["price"], str)


async def test_post_zero_price_returns_400_with_errors_price(client):
    resp = await client.post("/api/products", json=_valid_payload(price=0))
    assert resp.status_code == 400
    assert "price" in resp.json()["errors"]


async def test_post_invalid_category_returns_400_with_errors_category(client):
    resp = await client.post(
        "/api/products", json=_valid_payload(category="InvalidCategory")
    )
    assert resp.status_code == 400
    assert "category" in resp.json()["errors"]


async def test_put_negative_price_returns_400_with_errors_price(client):
    # Body-level validation must fire before existence check, so any well-formed
    # ObjectId in the path is fine here.
    resp = await client.put(
        f"/api/products/{NON_EXISTENT_ID}", json={"price": -10}
    )
    assert resp.status_code == 400
    assert "price" in resp.json()["errors"]


async def test_error_response_shape(client):
    # Multiple invalid fields at once → errors object should contain a string per field.
    resp = await client.post(
        "/api/products",
        json={"name": "", "price": -1, "category": "Bogus"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "message" in body and isinstance(body["message"], str)
    errors = body["errors"]
    assert isinstance(errors, dict)
    assert set(errors.keys()) >= {"name", "price", "category"}
    for field, msg in errors.items():
        assert isinstance(msg, str) and msg, f"errors.{field} must be a non-empty string"


async def test_post_with_all_valid_fields_returns_201(client):
    resp = await client.post("/api/products", json=_valid_payload(name="New Item"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "New Item"
    assert body["category"] == "Electronics"
    assert body["price"] == 9.99
    assert "id" in body


async def test_put_non_existent_product_returns_404(client):
    resp = await client.put(
        f"/api/products/{NON_EXISTENT_ID}",
        json={"name": "Update attempt"},
    )
    assert resp.status_code == 404
