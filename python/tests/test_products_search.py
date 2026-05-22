def _haystack(product: dict) -> str:
    return (product["name"] + " " + (product.get("description") or "")).lower()


async def test_q_matches_name_or_description_case_insensitive(client):
    resp = await client.get("/api/products/search", params={"q": "mouse"})
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    names = {p["name"] for p in results}
    assert "Wireless Mouse" in names      # match in name
    assert "Mouse Pad XL" in names        # match in name
    for product in results:
        assert "mouse" in _haystack(product)

    # Case-insensitivity: uppercase query yields the same set.
    upper = await client.get("/api/products/search", params={"q": "MOUSE"})
    assert {p["id"] for p in upper.json()} == {p["id"] for p in results}


async def test_category_is_exact_match(client):
    resp = await client.get("/api/products/search", params={"category": "Electronics"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert all(p["category"] == "Electronics" for p in results)

    # Wrong-case category should not match (exact, not partial).
    miss = await client.get("/api/products/search", params={"category": "electronics"})
    assert miss.json() == []


async def test_min_price_is_inclusive(client):
    resp = await client.get("/api/products/search", params={"minPrice": 50})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert all(p["price"] >= 50 for p in results)


async def test_max_price_is_inclusive(client):
    resp = await client.get("/api/products/search", params={"maxPrice": 20})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert all(p["price"] <= 20 for p in results)


async def test_q_combined_with_price_range(client):
    resp = await client.get(
        "/api/products/search",
        params={"q": "USB", "minPrice": 10, "maxPrice": 50},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    for product in results:
        assert "usb" in _haystack(product)
        assert 10 <= product["price"] <= 50

    # External SSD has "USB" in description but price 79.99 → must be excluded.
    assert "External SSD" not in {p["name"] for p in results}


async def test_no_matches_returns_empty_array(client):
    resp = await client.get("/api/products/search", params={"q": "nonexistentxyz"})
    assert resp.status_code == 200
    assert resp.json() == []
