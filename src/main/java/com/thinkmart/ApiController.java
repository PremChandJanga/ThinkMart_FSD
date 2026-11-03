package com.thinkmart;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.bouncycastle.crypto.generators.SCrypt;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.servlet.view.RedirectView;
import org.springframework.stereotype.Controller;

@RestController
@RequestMapping("/api")
public class ApiController {
    private static final String SESSION_COOKIE = "thinkmart_session";
    private static final long SESSION_MAX_AGE = 60L * 60 * 24 * 30;
    private static final SecureRandom RANDOM = new SecureRandom();

    private final JdbcTemplate jdbc;

    public ApiController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/products")
    public Map<String, Object> products() {
        return Map.of("products", jdbc.queryForList("""
                SELECT id, name, category, description, price_cents, original_price_cents,
                       rating, review_count, image_path
                FROM products ORDER BY rowid
                """));
    }

    @GetMapping("/auth/me")
    public Map<String, Object> currentUser(HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        Map<String, Object> result = new HashMap<>();
        result.put("user", session.userId() == null ? null : findUser(session.userId()));
        return result;
    }

    @PostMapping("/auth/register")
    @Transactional
    public ResponseEntity<Map<String, Object>> register(@RequestBody Map<String, Object> payload,
            HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        String fullName = text(payload, "fullName").trim();
        String email = text(payload, "email").trim().toLowerCase();
        String phone = text(payload, "phone").trim();
        String password = text(payload, "password");
        if (fullName.length() < 2 || !email.contains("@") || password.length() < 8) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Enter your name, a valid email, and a password of at least 8 characters.");
        }
        byte[] salt = new byte[16];
        RANDOM.nextBytes(salt);
        String passwordHash = hex(SCrypt.generate(password.getBytes(StandardCharsets.UTF_8), salt, 1 << 14, 8, 1, 64));
        long userId = jdbc.queryForObject("""
            INSERT INTO users (full_name, email, phone, password_hash, password_salt)
            VALUES (?, ?, ?, ?, ?) RETURNING id
            """, Long.class, fullName, email, phone, passwordHash, hex(salt));
        jdbc.update("UPDATE sessions SET user_id = ? WHERE id = ?", userId, session.id());
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("user", findUser(userId)));
    }

    @PostMapping("/auth/login")
    @Transactional
    public Map<String, Object> login(@RequestBody Map<String, Object> payload,
            HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        String email = text(payload, "email").trim().toLowerCase();
        String password = text(payload, "password");
        Map<String, Object> account = jdbc.query("SELECT id, full_name, email, password_hash, password_salt FROM users WHERE email = ?",
                result -> result.next() ? rowMap(result) : null, email);
        if (account == null || !passwordMatches(password, account)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Email or password is incorrect.");
        }
        long userId = number(account.get("id")).longValue();
        jdbc.update("UPDATE sessions SET user_id = ? WHERE id = ?", userId, session.id());
        return Map.of("user", publicUser(account));
    }

    @PostMapping("/auth/logout")
    @Transactional
    public Map<String, Object> logout(HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        jdbc.update("UPDATE sessions SET user_id = NULL WHERE id = ?", session.id());
        Map<String, Object> result = new HashMap<>();
        result.put("user", null);
        return result;
    }

    @GetMapping("/cart")
    public Map<String, Object> cart(HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        List<Map<String, Object>> items = jdbc.queryForList("""
                SELECT p.id, p.name, p.category, p.price_cents, p.image_path, c.quantity
                FROM cart_items c JOIN products p ON p.id = c.product_id
                WHERE c.session_id = ? ORDER BY p.name
                """, session.id());
        int itemCount = 0;
        long total = 0;
        for (Map<String, Object> item : items) {
            int quantity = number(item.get("quantity")).intValue();
            itemCount += quantity;
            total += number(item.get("price_cents")).longValue() * quantity;
        }
        return Map.of("items", items, "item_count", itemCount, "total_cents", total);
    }

    @PostMapping("/cart/items")
    @Transactional
    public Map<String, Object> addToCart(@RequestBody Map<String, Object> payload,
            HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        String productId = text(payload, "productId");
        int quantity = quantity(payload.getOrDefault("quantity", 1), 1, 10);
        if (jdbc.queryForObject("SELECT COUNT(*) FROM products WHERE id = ?", Integer.class, productId) == 0) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Product not found.");
        }
        jdbc.update("""
                INSERT INTO cart_items (session_id, product_id, quantity) VALUES (?, ?, ?)
                ON CONFLICT(session_id, product_id) DO UPDATE SET quantity = MIN(10, quantity + excluded.quantity)
                """, session.id(), productId, quantity);
        return Map.of("message", "Added to cart.");
    }

    @PatchMapping("/cart/items/{productId}")
    @Transactional
    public Map<String, Object> updateCartItem(@PathVariable String productId, @RequestBody Map<String, Object> payload,
            HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        int quantity = quantity(payload.get("quantity"), 0, 10);
        if (quantity == 0) {
            jdbc.update("DELETE FROM cart_items WHERE session_id = ? AND product_id = ?", session.id(), productId);
        } else {
            jdbc.update("UPDATE cart_items SET quantity = ? WHERE session_id = ? AND product_id = ?",
                    quantity, session.id(), productId);
        }
        return Map.of("message", "Cart updated.");
    }

    @DeleteMapping("/cart/items/{productId}")
    @Transactional
    public Map<String, Object> removeCartItem(@PathVariable String productId,
            HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        jdbc.update("DELETE FROM cart_items WHERE session_id = ? AND product_id = ?", session.id(), productId);
        return Map.of("message", "Item removed.");
    }

    @PostMapping("/orders")
    @Transactional
    public ResponseEntity<Map<String, Object>> checkout(HttpServletRequest request, HttpServletResponse response) {
        Session session = session(request, response);
        if (session.userId() == null) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "Sign in before placing your order.");
        }
        List<Map<String, Object>> items = jdbc.queryForList("""
                SELECT product_id, quantity, price_cents FROM cart_items
                JOIN products ON products.id = cart_items.product_id WHERE session_id = ?
                """, session.id());
        if (items.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Your cart is empty.");
        }
        long total = items.stream().mapToLong(item -> number(item.get("quantity")).longValue()
                * number(item.get("price_cents")).longValue()).sum();
        long orderId = jdbc.queryForObject("INSERT INTO orders (user_id, total_cents) VALUES (?, ?) RETURNING id",
            Long.class, session.userId(), total);
        for (Map<String, Object> item : items) {
            jdbc.update("INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) VALUES (?, ?, ?, ?)",
                    orderId, item.get("product_id"), item.get("quantity"), item.get("price_cents"));
        }
        jdbc.update("DELETE FROM cart_items WHERE session_id = ?", session.id());
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("orderId", orderId, "total_cents", total));
    }

    @PostMapping("/contact")
    @Transactional
    public ResponseEntity<Map<String, Object>> contact(@RequestBody Map<String, Object> payload) {
        String name = text(payload, "name").trim();
        String email = text(payload, "email").trim();
        String subject = text(payload, "subject").trim();
        String message = text(payload, "message").trim();
        if (name.length() < 2 || !email.contains("@") || message.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Enter your name, a valid email, and a message.");
        }
        if (subject.isEmpty()) subject = "Other";
        jdbc.update("INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
                name, email, subject, message);
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("message", "Thanks. Your message has been received."));
    }

    private Session session(HttpServletRequest request, HttpServletResponse response) {
        String token = null;
        Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            for (Cookie cookie : cookies) {
                if (SESSION_COOKIE.equals(cookie.getName())) token = cookie.getValue();
            }
        }
        if (token != null) {
            List<Map<String, Object>> rows = jdbc.queryForList(
                    "SELECT id, user_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
                    sha256(token), Instant.now().getEpochSecond());
            if (!rows.isEmpty()) {
                Map<String, Object> row = rows.get(0);
                Object userId = row.get("user_id");
                return new Session(number(row.get("id")).longValue(), userId == null ? null : number(userId).longValue());
            }
        }
        byte[] tokenBytes = new byte[32];
        RANDOM.nextBytes(tokenBytes);
        token = Base64.getUrlEncoder().withoutPadding().encodeToString(tokenBytes);
        long now = Instant.now().getEpochSecond();
        long sessionId = jdbc.queryForObject("""
            INSERT INTO sessions (token_hash, created_at, expires_at)
            VALUES (?, ?, ?) RETURNING id
            """, Long.class, sha256(token), now, now + SESSION_MAX_AGE);
        response.addHeader("Set-Cookie", SESSION_COOKIE + "=" + token
                + "; Path=/; HttpOnly; SameSite=Lax; Max-Age=" + SESSION_MAX_AGE);
        return new Session(sessionId, null);
    }

    private Map<String, Object> findUser(long userId) {
        List<Map<String, Object>> users = jdbc.queryForList("SELECT id, full_name, email FROM users WHERE id = ?", userId);
        return users.isEmpty() ? Map.of() : users.get(0);
    }

    private static Map<String, Object> publicUser(Map<String, Object> account) {
        Map<String, Object> user = new HashMap<>();
        user.put("id", account.get("id"));
        user.put("full_name", account.get("full_name"));
        user.put("email", account.get("email"));
        return user;
    }

    private static boolean passwordMatches(String password, Map<String, Object> account) {
        byte[] salt = fromHex(String.valueOf(account.get("password_salt")));
        byte[] expected = fromHex(String.valueOf(account.get("password_hash")));
        byte[] actual = SCrypt.generate(password.getBytes(StandardCharsets.UTF_8), salt, 1 << 14, 8, 1, 64);
        return MessageDigest.isEqual(expected, actual);
    }

    private static String text(Map<String, Object> payload, String key) {
        Object value = payload.get(key);
        return value == null ? "" : String.valueOf(value);
    }

    private static int quantity(Object value, int minimum, int maximum) {
        if (!(value instanceof Number number) || number.doubleValue() != number.intValue()
                || number.intValue() < minimum || number.intValue() > maximum) {
            throw new ApiException(HttpStatus.BAD_REQUEST,
                    "Quantity must be between " + minimum + " and " + maximum + ".");
        }
        return number.intValue();
    }

    private static Number number(Object value) {
        return (Number) value;
    }

    private static String sha256(String value) {
        try {
            return hex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static String hex(byte[] value) {
        StringBuilder result = new StringBuilder(value.length * 2);
        for (byte item : value) result.append(String.format("%02x", item));
        return result.toString();
    }

    private static byte[] fromHex(String value) {
        byte[] result = new byte[value.length() / 2];
        for (int index = 0; index < result.length; index++) {
            result[index] = (byte) Integer.parseInt(value.substring(index * 2, index * 2 + 2), 16);
        }
        return result;
    }

    private static Map<String, Object> rowMap(java.sql.ResultSet result) throws java.sql.SQLException {
        Map<String, Object> row = new HashMap<>();
        for (int index = 1; index <= result.getMetaData().getColumnCount(); index++) {
            row.put(result.getMetaData().getColumnLabel(index), result.getObject(index));
        }
        return row;
    }

    private record Session(long id, Long userId) {}
}

@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(ApiException.class)
    ResponseEntity<Map<String, String>> handleApiException(ApiException exception) {
        return ResponseEntity.status(exception.status).body(Map.of("error", exception.getMessage()));
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    ResponseEntity<Map<String, String>> handleConflict(DataIntegrityViolationException exception) {
        return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(Map.of("error", "That account or item already exists."));
    }
}

@Controller
class HomeController {
    @GetMapping("/")
    RedirectView home() {
        return new RedirectView("/Home-Page.html");
    }
}

class ApiException extends RuntimeException {
    final HttpStatus status;

    ApiException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }
}