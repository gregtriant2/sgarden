async def test_stats_returns_200_with_positive_total_count(client, seed_products):
    resp = await client.get("/api/products/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["totalCount"], int)
    assert body["totalCount"] > 0
    assert body["totalCount"] == len(seed_products)


async def test_stats_average_price_is_positive(client):
    resp = await client.get("/api/products/stats")
    body = resp.json()
    assert isinstance(body["averagePrice"], (int, float))
    assert body["averagePrice"] > 0
    # Sanity: average sits inside the price range.
    assert body["minPrice"] <= body["averagePrice"] <= body["maxPrice"]


async def test_stats_max_price_at_least_min_price(client, seed_products):
    resp = await client.get("/api/products/stats")
    body = resp.json()
    assert body["maxPrice"] >= body["minPrice"]
    # And both match the seed extremes.
    seed_prices = [p["price"] for p in seed_products]
    assert body["minPrice"] == min(seed_prices)
    assert body["maxPrice"] == max(seed_prices)


async def test_stats_category_count_is_object_with_category_keys(client, seed_products):
    resp = await client.get("/api/products/stats")
    body = resp.json()
    category_count = body["categoryCount"]
    assert isinstance(category_count, dict)
    assert len(category_count) > 0
    seed_categories = {p["category"] for p in seed_products}
    assert set(category_count.keys()) == seed_categories
    assert all(isinstance(v, int) and v > 0 for v in category_count.values())


async def test_stats_category_counts_sum_to_total(client):
    resp = await client.get("/api/products/stats")
    body = resp.json()
    assert sum(body["categoryCount"].values()) == body["totalCount"]
