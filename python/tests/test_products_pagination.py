async def test_response_has_data_page_limit_total(client):
    resp = await client.get("/api/products", params={"page": 1, "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert body["page"] == 1
    assert body["limit"] == 5
    assert isinstance(body["total"], int)
    assert len(body["data"]) == 5


async def test_pages_do_not_overlap(client):
    page1 = (await client.get("/api/products", params={"page": 1, "limit": 5})).json()
    page2 = (await client.get("/api/products", params={"page": 2, "limit": 5})).json()

    ids1 = {p["id"] for p in page1["data"]}
    ids2 = {p["id"] for p in page2["data"]}
    assert len(ids1) == 5
    assert len(ids2) == 5
    assert ids1.isdisjoint(ids2)


async def test_sort_by_price_ascending(client):
    resp = await client.get(
        "/api/products", params={"sort": "price", "order": "asc", "limit": 100}
    )
    prices = [p["price"] for p in resp.json()["data"]]
    assert prices == sorted(prices)


async def test_sort_by_price_descending(client):
    resp = await client.get(
        "/api/products", params={"sort": "price", "order": "desc", "limit": 100}
    )
    prices = [p["price"] for p in resp.json()["data"]]
    assert prices == sorted(prices, reverse=True)


async def test_sort_by_name_ascending(client):
    resp = await client.get(
        "/api/products", params={"sort": "name", "order": "asc", "limit": 100}
    )
    names = [p["name"] for p in resp.json()["data"]]
    assert names == sorted(names)


async def test_total_exceeds_page_when_limit_is_small(client, seed_products):
    resp = await client.get("/api/products", params={"page": 1, "limit": 5})
    body = resp.json()
    assert body["total"] > len(body["data"])
    assert body["total"] == len(seed_products)


async def test_page_beyond_data_returns_empty_array(client):
    resp = await client.get("/api/products", params={"page": 999, "limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["page"] == 999
    assert body["limit"] == 10
    assert body["total"] > 0
