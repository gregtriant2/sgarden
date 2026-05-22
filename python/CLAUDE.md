# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from the `python/` directory:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 4000 --reload   # dev server with autoreload
python main.py                                          # alternative entry point
```

No test suite, linter, or formatter is configured.

## Environment

`config.py` loads `.env` from the **parent directory** (`../.env`), not from `python/`. Copy `../.env.sample` to `../.env` to configure. Variables: `DATABASE_URL` (Mongo URI; the DB name is parsed from the URI path, defaulting to `sgarden`), `PORT`, `SERVER_SECRET` (JWT HS256 key), `JWT_EXPIRATION_HOURS`.

MongoDB must be reachable at startup — `main.py`'s lifespan handler calls `init_indexes()` and `seed_data()` before the app accepts traffic, and both will block/raise if Mongo is down.

## Architecture

FastAPI + Motor (async MongoDB) service. Sibling `../java/` is a Spring Boot implementation that exposes **the same REST contract on the same database**; behavior changes should usually be mirrored across both stacks, and field naming is shared (Mongo documents use camelCase keys like `createdAt`, `lastActiveAt` even though Python models use snake_case attributes).

Layer layout:
- `main.py` — app factory, CORS, router registration, lifespan-driven index + seed bootstrap.
- `config.py` — `pydantic-settings` config singleton (`settings`).
- `database.py` — module-level Motor client and collection handles (`users_collection`, `products_collection`). Importing this module opens the connection; there is no DI for the DB.
- `models/` — Pydantic schemas. Separate `*Request` / `*Response` / `*InDB` classes per entity.
- `routes/` — one router per resource (`auth`, `products`, `users`). Routers are mounted under `/api/...` prefixes inside each module, not in `main.py`.
- `security/jwt_handler.py` — `create_token` / `decode_token` and the `get_current_user` FastAPI dependency. Protected endpoints take `current_user: dict = Depends(get_current_user)`.
- `seed.py` — idempotent seeding of two test users (`admin`/`admin123`, `user`/`user1234`) and ~15 sample products, run on every startup.
- `services/` — empty placeholder package; business logic currently lives inline in route handlers.

Auth flow: `routes/auth.py` hashes passwords with bcrypt and issues HS256 JWTs containing `sub` (user id), `username`, `role`. `get_current_user` decodes the token and re-fetches the user from Mongo on every request (no caching).

ID handling: Mongo `_id` is an `ObjectId`; routes validate with `ObjectId.is_valid` before querying and stringify it in responses. Always do both — passing a raw string to `find_one({"_id": ...})` will silently miss.

## Important: Intentional defects

This codebase contains **deliberately planted security vulnerabilities and code-quality issues** marked with `# SECURITY ISSUE:` and `# CODE QUALITY ISSUE:` comments. Examples: NoSQL injection in `/api/users/search`, command injection in `/api/users/system/info`, path traversal in `/api/users/reports/download`, MD5 hashing endpoint, missing admin checks on user delete / role-change, password hash leaked in user responses, plus many duplicated functions/models and unused variables.

Treat these as fixture data for code-review tooling. Do **not** "clean them up" unless the user explicitly asks — they are the subject of the exercise. When asked to add a feature, do not propagate the patterns (e.g. don't add another shell-exec endpoint just because one exists).
