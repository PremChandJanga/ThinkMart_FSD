import hashlib
import json
import mimetypes
import os
import secrets
import sqlite3
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / ".data" / "thinkmart.sqlite3"
HOST = os.environ.get("THINKMART_HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
SESSION_COOKIE = "thinkmart_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30

PRODUCTS = [
    ("novabook-air-14", "NovaBook Air 14", "Laptops", "Lightweight laptop with 16GB memory and 512GB storage.", 5499900, 6699900, 4.8, 214, "💻", "assets/products/novabook-air-14.jpg"),
    ("forgebook-pro-16", "ForgeBook Pro 16", "Laptops", "A powerful 16-inch laptop built for demanding work.", 8999000, 9999000, 4.5, 98, "💻", "assets/products/forgebook-pro-16.jpg"),
    ("pulse-x-pro-5g", "Pulse X Pro 5G", "Mobiles", "Fast 5G performance with a vivid, high-resolution display.", 3249000, 3699900, 4.6, 512, "📱", "assets/products/pulse-x-pro-5g.jpg"),
    ("aura-lite-se", "Aura Lite SE", "Mobiles", "A capable everyday phone with a bright edge-to-edge screen.", 1899900, 2249900, 4.7, 301, "📱", "assets/products/aura-lite-se.jpg"),
    ("orbit-smartwatch-s3", "Orbit SmartWatch S3", "Watches", "A versatile smartwatch with health and activity tracking.", 679900, 899900, 4.9, 187, "⌚", "assets/products/orbit-smartwatch-s3.jpg"),
    ("chrono-classic-steel", "Chrono Classic Steel", "Watches", "A refined steel watch with a comfortable everyday fit.", 429900, 539900, 4.4, 76, "⌚", "assets/products/chrono-classic-steel.jpg"),
    ("wavebuds-anc", "WaveBuds ANC", "Accessories", "Wireless earbuds with active noise cancellation.", 279900, 399900, 4.8, 420, "🎧", "assets/products/wavebuds-anc.jpg"),
    ("trailpack-laptop-bag", "TrailPack Laptop Bag", "Accessories", "A padded, weather-resistant bag for your daily commute.", 189900, 244900, 4.5, 143, "🎒", "assets/products/trailpack-laptop-bag.jpg"),
    ("novabook-air-13", "NovaBook Air 13", "Laptops", "A compact 13-inch laptop for study, travel, and everyday work.", 4999000, 5999000, 4.6, 132, "💻", "assets/products/laptop-studio-14.jpg"),
    ("forgebook-studio-14", "ForgeBook Studio 14", "Laptops", "A color-accurate display and fast processor for creative projects.", 7499000, 8499000, 4.7, 86, "💻", "assets/products/laptop-travel-13.jpg"),
    ("thinklite-15", "ThinkLite 15", "Laptops", "A roomy 15-inch screen with all-day battery life.", 6749000, 7899000, 4.5, 74, "💻", "assets/products/novabook-air-14.jpg"),
    ("zenbook-go-14", "ZenBook Go 14", "Laptops", "A slim everyday notebook with a bright 14-inch display.", 5999000, 6999000, 4.6, 91, "💻", "assets/products/forgebook-pro-16.jpg"),
    ("creatorbook-pro-16", "CreatorBook Pro 16", "Laptops", "A high-performance laptop for editing, design, and multitasking.", 10999000, 12499000, 4.8, 57, "💻", "assets/products/laptop-studio-14.jpg"),
    ("workmate-flex-14", "WorkMate Flex 14", "Laptops", "A flexible 2-in-1 laptop for meetings and mobile work.", 8299000, 9499000, 4.5, 63, "💻", "assets/products/laptop-travel-13.jpg"),
    ("travelbook-13", "TravelBook 13", "Laptops", "A lightweight laptop made for commuters and frequent travelers.", 5299000, 6199000, 4.4, 48, "💻", "assets/products/novabook-air-14.jpg"),
    ("gameforge-15", "GameForge 15", "Laptops", "A fast gaming laptop with a high-refresh display.", 9699000, 10999000, 4.7, 102, "💻", "assets/products/forgebook-pro-16.jpg"),
    ("nova-phone-12", "Nova Phone 12", "Mobiles", "A balanced 5G phone with a crisp camera and vivid screen.", 2899000, 3299000, 4.6, 183, "📱", "assets/products/phone-aura-max-5g.jpg"),
    ("pulse-x-mini", "Pulse X Mini", "Mobiles", "A pocket-friendly phone with smooth everyday performance.", 2299000, 2699000, 4.5, 121, "📱", "assets/products/phone-pulse-mini.jpg"),
    ("aura-max-5g", "Aura Max 5G", "Mobiles", "A large-screen 5G phone with a long-lasting battery.", 3899000, 4499000, 4.7, 146, "📱", "assets/products/phone-aura-max-5g.jpg"),
    ("pixelight-9", "Pixelight 9", "Mobiles", "A camera-focused smartphone with clean, fast software.", 4599000, 5299000, 4.8, 212, "📱", "assets/products/pulse-x-pro-5g.jpg"),
    ("oneplus-neo-5g", "OnePlus Neo 5G", "Mobiles", "A responsive 5G phone built for streaming and everyday use.", 3499000, 3999000, 4.6, 167, "📱", "assets/products/phone-aura-max-5g.jpg"),
    ("nova-fold-5g", "Nova Fold 5G", "Mobiles", "A foldable phone that opens into a generous tablet-sized display.", 9999000, 11499000, 4.7, 58, "📱", "assets/products/phone-pulse-mini.jpg"),
    ("orbit-edge-5g", "Orbit Edge 5G", "Mobiles", "A slim 5G phone with a bright edge-to-edge display.", 2699000, 3099000, 4.4, 94, "📱", "assets/products/aura-lite-se.jpg"),
    ("daystar-lite", "Daystar Lite", "Mobiles", "An affordable smartphone for messaging, photos, and browsing.", 1499000, 1799000, 4.3, 203, "📱", "assets/products/pulse-x-pro-5g.jpg"),
    ("orbit-fit-pro", "Orbit Fit Pro", "Watches", "A fitness smartwatch with activity tracking and sleep insights.", 899900, 1199900, 4.7, 116, "⌚", "assets/products/watch-orbit-fit.jpg"),
    ("trackline-active", "Trackline Active", "Watches", "A lightweight sports watch with GPS workout tracking.", 749900, 999900, 4.5, 82, "⌚", "assets/products/watch-chrono-steel.jpg"),
    ("chrono-steel-42", "Chrono Steel 42", "Watches", "A 42 mm stainless steel watch with a clean everyday dial.", 589900, 729900, 4.6, 71, "⌚", "assets/products/orbit-smartwatch-s3.jpg"),
    ("pulse-watch-2", "Pulse Watch 2", "Watches", "A practical smartwatch with heart-rate and activity monitoring.", 549900, 699900, 4.5, 93, "⌚", "assets/products/chrono-classic-steel.jpg"),
    ("aero-watch-lite", "Aero Watch Lite", "Watches", "A slim, lightweight smartwatch for daily notifications and steps.", 399900, 499900, 4.3, 64, "⌚", "assets/products/watch-orbit-fit.jpg"),
    ("summit-gps-watch", "Summit GPS Watch", "Watches", "A rugged GPS watch designed for outdoor training.", 1299900, 1599900, 4.7, 52, "⌚", "assets/products/watch-chrono-steel.jpg"),
    ("timecraft-classic", "Timecraft Classic", "Watches", "A minimal analog watch with a comfortable leather strap.", 329900, 429900, 4.4, 109, "⌚", "assets/products/orbit-smartwatch-s3.jpg"),
    ("orbit-mini", "Orbit Mini", "Watches", "A compact smartwatch with essential health and activity features.", 619900, 799900, 4.6, 88, "⌚", "assets/products/chrono-classic-steel.jpg"),
    ("wavebuds-air", "WaveBuds Air", "Accessories", "Compact wireless earbuds with a pocket-sized charging case.", 199900, 299900, 4.5, 152, "🎧", "assets/products/wavebuds-anc.jpg"),
    ("studio-sound-headphones", "StudioSound Headphones", "Accessories", "Comfortable over-ear headphones for work and travel.", 349900, 499900, 4.6, 98, "🎧", "assets/products/accessory-studio-sound.jpg"),
    ("chargedock-3-in-1", "ChargeDock 3-in-1", "Accessories", "A compact charging station for your phone, watch, and earbuds.", 299900, 399900, 4.4, 61, "🔌", "assets/products/wavebuds-anc.jpg"),
    ("powerbank-20k", "PowerBank 20K", "Accessories", "A high-capacity portable charger for phones and small devices.", 249900, 349900, 4.7, 176, "🔋", "assets/products/phone-aura-max-5g.jpg"),
    ("clearcase-phone-case", "ClearCase Phone Case", "Accessories", "A slim protective case with a clear, scratch-resistant finish.", 79900, 119900, 4.3, 220, "📱", "assets/products/phone-pulse-mini.jpg"),
    ("swiftcharge-65w", "SwiftCharge 65W", "Accessories", "A compact USB-C fast charger for compatible phones and laptops.", 169900, 229900, 4.6, 137, "🔌", "assets/products/laptop-studio-14.jpg"),
    ("travelhub-usbc", "TravelHub USB-C", "Accessories", "A multiport USB-C hub for displays, storage, and accessories.", 219900, 299900, 4.5, 84, "🔌", "assets/products/laptop-travel-13.jpg"),
    ("citypack-sling", "CityPack Sling", "Accessories", "A compact everyday backpack with room for a tablet and essentials.", 159900, 219900, 4.4, 73, "🎒", "assets/products/accessory-citypack.jpg"),
]


def connect_db():
    DATABASE.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_db():
    with connect_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
                original_price_cents INTEGER NOT NULL CHECK (original_price_cents >= price_cents),
                rating REAL NOT NULL DEFAULT 0,
                review_count INTEGER NOT NULL DEFAULT 0,
                emoji TEXT NOT NULL,
                image_path TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                phone TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT NOT NULL UNIQUE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cart_items (
                session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL REFERENCES products(id),
                quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 10),
                PRIMARY KEY (session_id, product_id)
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                total_cents INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id TEXT NOT NULL REFERENCES products(id),
                quantity INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL,
                PRIMARY KEY (order_id, product_id)
            );
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        product_columns = {row["name"] for row in db.execute("PRAGMA table_info(products)")}
        if "image_path" not in product_columns:
            db.execute("ALTER TABLE products ADD COLUMN image_path TEXT NOT NULL DEFAULT ''")
        db.executemany("""
            INSERT INTO products
                (id, name, category, description, price_cents, original_price_cents, rating, review_count, emoji, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET image_path = excluded.image_path
        """, PRODUCTS)


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class ThinkMartHandler(BaseHTTPRequestHandler):
    server_version = "ThinkMart/1.0"

    def log_message(self, format_string, *args):
        print("%s - %s" % (self.address_string(), format_string % args))

    def send_json(self, payload, status=HTTPStatus.OK, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if headers:
            for name, value in headers.items():
                self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request is too large.")
            if length == 0:
                return {}
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object.")
            return payload
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "Send a valid JSON object.")

    def get_session(self, db):
        cookies = parse_qs(self.headers.get("Cookie", "").replace("; ", "&").replace("=", "=", 1))
        token = cookies.get(SESSION_COOKIE, [None])[0]
        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            session = db.execute(
                "SELECT id, user_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (token_hash, int(time.time())),
            ).fetchone()
            if session:
                return session, None

        token = secrets.token_urlsafe(32)
        now = int(time.time())
        cursor = db.execute(
            "INSERT INTO sessions (token_hash, created_at, expires_at) VALUES (?, ?, ?)",
            (hashlib.sha256(token.encode()).hexdigest(), now, now + SESSION_MAX_AGE),
        )
        session = db.execute("SELECT id, user_id FROM sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        cookie = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_MAX_AGE}"
        return session, cookie

    def handle_api(self, method, path):
        db = connect_db()
        cookie = None
        try:
            session, cookie = self.get_session(db)
            user = db.execute("SELECT id, full_name, email FROM users WHERE id = ?", (session["user_id"],)).fetchone() if session["user_id"] else None
            payload = self.read_json() if method in {"POST", "PATCH", "PUT"} else {}
            parts = [unquote(part) for part in path.strip("/").split("/") if part]
            status, result = self.route_api(db, session, user, method, parts, payload)
            db.commit()
            headers = {"Set-Cookie": cookie} if cookie else None
            self.send_json(result, status, headers)
        except ApiError as error:
            db.rollback()
            headers = {"Set-Cookie": cookie} if cookie else None
            self.send_json({"error": error.message}, error.status, headers)
        except sqlite3.IntegrityError:
            db.rollback()
            self.send_json({"error": "That account or item already exists."}, HTTPStatus.CONFLICT)
        except Exception:
            db.rollback()
            self.send_json({"error": "The server could not complete this request."}, HTTPStatus.INTERNAL_SERVER_ERROR)
            raise
        finally:
            db.close()

    def route_api(self, db, session, user, method, parts, payload):
        if parts == ["api", "products"] and method == "GET":
            rows = db.execute("""
                SELECT id, name, category, description, price_cents, original_price_cents,
                       rating, review_count, image_path
                FROM products ORDER BY rowid
            """).fetchall()
            return HTTPStatus.OK, {"products": [dict(row) for row in rows]}

        if parts == ["api", "auth", "me"] and method == "GET":
            return HTTPStatus.OK, {"user": dict(user) if user else None}

        if parts == ["api", "auth", "register"] and method == "POST":
            full_name = str(payload.get("fullName", "")).strip()
            email = str(payload.get("email", "")).strip().lower()
            phone = str(payload.get("phone", "")).strip()
            password = str(payload.get("password", ""))
            if len(full_name) < 2 or "@" not in email or len(password) < 8:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Enter your name, a valid email, and a password of at least 8 characters.")
            salt = secrets.token_bytes(16)
            password_hash = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()
            cursor = db.execute(
                "INSERT INTO users (full_name, email, phone, password_hash, password_salt) VALUES (?, ?, ?, ?, ?)",
                (full_name, email, phone, password_hash, salt.hex()),
            )
            db.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (cursor.lastrowid, session["id"]))
            created = db.execute("SELECT id, full_name, email FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return HTTPStatus.CREATED, {"user": dict(created)}

        if parts == ["api", "auth", "login"] and method == "POST":
            email = str(payload.get("email", "")).strip().lower()
            password = str(payload.get("password", ""))
            account = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if not account:
                raise ApiError(HTTPStatus.UNAUTHORIZED, "Email or password is incorrect.")
            candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(account["password_salt"]), n=2**14, r=8, p=1).hex()
            if not secrets.compare_digest(candidate, account["password_hash"]):
                raise ApiError(HTTPStatus.UNAUTHORIZED, "Email or password is incorrect.")
            db.execute("UPDATE sessions SET user_id = ? WHERE id = ?", (account["id"], session["id"]))
            return HTTPStatus.OK, {"user": {"id": account["id"], "full_name": account["full_name"], "email": account["email"]}}

        if parts == ["api", "auth", "logout"] and method == "POST":
            db.execute("UPDATE sessions SET user_id = NULL WHERE id = ?", (session["id"],))
            return HTTPStatus.OK, {"user": None}

        if parts == ["api", "cart"] and method == "GET":
            rows = db.execute("""
                SELECT p.id, p.name, p.category, p.price_cents, p.image_path, c.quantity
                FROM cart_items c JOIN products p ON p.id = c.product_id
                WHERE c.session_id = ? ORDER BY p.name
            """, (session["id"],)).fetchall()
            items = [dict(row) for row in rows]
            return HTTPStatus.OK, {"items": items, "item_count": sum(item["quantity"] for item in items), "total_cents": sum(item["price_cents"] * item["quantity"] for item in items)}

        if parts == ["api", "cart", "items"] and method == "POST":
            product_id = str(payload.get("productId", ""))
            quantity = payload.get("quantity", 1)
            if not isinstance(quantity, int) or not 1 <= quantity <= 10:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Quantity must be between 1 and 10.")
            if not db.execute("SELECT 1 FROM products WHERE id = ?", (product_id,)).fetchone():
                raise ApiError(HTTPStatus.NOT_FOUND, "Product not found.")
            db.execute("""
                INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(session_id, product_id) DO UPDATE SET quantity = MIN(10, quantity + excluded.quantity)
            """, (session["id"], product_id, quantity))
            return HTTPStatus.OK, {"message": "Added to cart."}

        if len(parts) == 4 and parts[:3] == ["api", "cart", "items"]:
            product_id = parts[3]
            if method == "PATCH":
                quantity = payload.get("quantity")
                if not isinstance(quantity, int) or not 0 <= quantity <= 10:
                    raise ApiError(HTTPStatus.BAD_REQUEST, "Quantity must be between 0 and 10.")
                if quantity == 0:
                    db.execute("DELETE FROM cart_items WHERE session_id = ? AND product_id = ?", (session["id"], product_id))
                else:
                    db.execute("UPDATE cart_items SET quantity = ? WHERE session_id = ? AND product_id = ?", (quantity, session["id"], product_id))
                return HTTPStatus.OK, {"message": "Cart updated."}
            if method == "DELETE":
                db.execute("DELETE FROM cart_items WHERE session_id = ? AND product_id = ?", (session["id"], product_id))
                return HTTPStatus.OK, {"message": "Item removed."}

        if parts == ["api", "orders"] and method == "POST":
            if not user:
                raise ApiError(HTTPStatus.UNAUTHORIZED, "Sign in before placing your order.")
            items = db.execute("""
                SELECT product_id, quantity, price_cents FROM cart_items
                JOIN products ON products.id = cart_items.product_id WHERE session_id = ?
            """, (session["id"],)).fetchall()
            if not items:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Your cart is empty.")
            total = sum(item["quantity"] * item["price_cents"] for item in items)
            cursor = db.execute("INSERT INTO orders (user_id, total_cents) VALUES (?, ?)", (user["id"], total))
            db.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                [(cursor.lastrowid, item["product_id"], item["quantity"], item["price_cents"]) for item in items],
            )
            db.execute("DELETE FROM cart_items WHERE session_id = ?", (session["id"],))
            return HTTPStatus.CREATED, {"orderId": cursor.lastrowid, "total_cents": total}

        if parts == ["api", "contact"] and method == "POST":
            name = str(payload.get("name", "")).strip()
            email = str(payload.get("email", "")).strip()
            subject = str(payload.get("subject", "Other")).strip()
            message = str(payload.get("message", "")).strip()
            if len(name) < 2 or "@" not in email or not message:
                raise ApiError(HTTPStatus.BAD_REQUEST, "Enter your name, a valid email, and a message.")
            db.execute("INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)", (name, email, subject, message))
            return HTTPStatus.CREATED, {"message": "Thanks. Your message has been received."}

        raise ApiError(HTTPStatus.NOT_FOUND, "API route not found.")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.handle_api("GET", parsed.path)
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        self.handle_api("POST", parsed.path)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        self.handle_api("PATCH", parsed.path)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        self.handle_api("DELETE", parsed.path)

    def serve_static(self, requested_path):
        requested_path = "/Home-Page.html" if requested_path == "/" else requested_path
        file_path = (ROOT / unquote(requested_path.lstrip("/"))).resolve()
        if not file_path.is_relative_to(ROOT) or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    initialize_db()
    print(f"Think Mart is running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), ThinkMartHandler).serve_forever()