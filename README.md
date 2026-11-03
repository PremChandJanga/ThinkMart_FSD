# Think Mart

Think Mart is a small full-stack shopping demo. It uses plain HTML, CSS, and JavaScript in the browser, plus a Spring Boot backend and a local SQLite database.

## Run locally

Install JDK 17 or newer and Maven, then run this from the project folder:

```sh
mvn spring-boot:run
```

Open http://127.0.0.1:8000. Stop the server with `Ctrl+C`. Maven downloads the required dependencies on the first run.

The server creates `.data/thinkmart.sqlite3` on first launch and seeds the product catalog. The database directory is ignored by Git. Delete that database file to reset local users, carts, messages, and orders; products are seeded again at next startup. Existing SQLite data is retained, and existing accounts continue to use their current scrypt password hashes.

## Included flows

- A 40-item catalog with 10 laptops, 10 mobiles, 10 watches, and 10 accessories; includes search, category filters, and a persistent session cart
- Account registration, login, and logout; passwords are salted and hashed with scrypt
- SQLite-backed contact messages
- Checkout creates a local demo order and clears the cart; no payment is collected

## API

- `GET /api/products`
- `GET /api/cart`
- `POST /api/cart/items`, `PATCH /api/cart/items/{productId}`, `DELETE /api/cart/items/{productId}`
- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/orders`
- `POST /api/contact`

This local demo server is intended for development, not public production hosting. Production deployment would need HTTPS, stronger operational protections, and a real payment provider before accepting orders.

Product photographs are sourced from Unsplash and stored locally in `assets/products/` for reliable loading.