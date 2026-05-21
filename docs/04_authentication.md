# 04 — Authentication: Login, Passwords, and How It All Works

> From "user types password" to "user is logged in" — every step explained at the deepest level.

---

## The Big Picture

Authentication answers the question: **"Who are you, and can I trust that you are who you say you are?"**

Our system uses a username + password login. The password is never stored as plain text anywhere. Instead, it is stored as a bcrypt hash in the `users` table in PostgreSQL. When someone logs in, we verify their password against the stored hash.

---

## Where User Data Lives: the `users` table (PostgreSQL)

```sql
CREATE TABLE users (
    username       TEXT PRIMARY KEY,
    password_hash  TEXT NOT NULL,
    display_name   TEXT NOT NULL DEFAULT '',
    customers      TEXT[] NOT NULL DEFAULT '{ALL}',
    role           TEXT NOT NULL DEFAULT 'sre',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

A typical row:

```
 username |                       password_hash                          | display_name        | customers | role
----------+--------------------------------------------------------------+---------------------+-----------+------------
 alice    | $2b$12$4fzFhO.q8el8cASDithqFeAU0EO5Cjg76G7NdMKpp27J1QYEYMuve | Alice (Senior SRE)  | {ALL}     | senior_sre
 admin    | $2b$12$NEMkyADvvMZMllCkkE/yVeTdwAS0G1pj64h2gC9.JJer62ltflrd6 | Admin               | {ALL}     | admin
```

Notice:
- **No plain-text password anywhere** — only `password_hash`
- `customers = '{ALL}'` means this user can search all documents (`TEXT[]` is a PostgreSQL native array)
- `role` controls what pages they can access (e.g., only `admin` can open the Admin Panel)

Previously the same data lived in `users.json` on disk. The migration to PostgreSQL is documented in `docs/migrateforpostgresql.md`.

---

## What Is bcrypt? Why Not a Simple Hash?

### The Problem With Simple Hashing

You might think: "Just run the password through SHA-256 and store that." Here's why that's dangerous.

SHA-256 is extremely fast — your laptop can compute **billions** of SHA-256 hashes per second. An attacker with a list of common passwords (called a "dictionary") can try:

```
SHA-256("password")   = 5e884898...  ← does it match? No
SHA-256("password1")  = 0b14d501...  ← does it match? No
SHA-256("charlie123") = 7f83b165...  ← does it match? YES → cracked
```

At billions of hashes per second, cracking short passwords takes milliseconds.

### How bcrypt Solves This

bcrypt is **intentionally slow** — designed to take about 100ms per hash. That doesn't matter for login (you wait 100ms and you're in). But for an attacker trying millions of passwords:

- SHA-256: 1 billion attempts per second
- bcrypt (cost 12): ~10 attempts per second

This makes brute-force attacks computationally infeasible.

### What Does a bcrypt Hash Look Like?

```
$2b$12$4fzFhO.q8el8cASDithqFeAU0EO5Cjg76G7NdMKpp27J1QYEYMuve
│  │  │                    │
│  │  └── salt (22 chars)  └── hash (31 chars)
│  └── cost factor: 2^12 = 4096 iterations of Blowfish cipher
└── bcrypt version 2b
```

- **The salt** is a random 22-character string generated fresh for each password. Two users with the exact same password will have completely different hashes because their salts are different.
- **The cost factor** (12) means bcrypt runs 4096 internal iterations. Higher = slower and safer.
- **The salt is embedded in the hash** — you don't need to store it separately.

### Why Salts Matter

Without salts, an attacker can precompute a table of common passwords and their hashes (a "rainbow table"):

```
Hash Table (no salt):
SHA256("password") = 5e884898...
SHA256("abc123")   = 6367c48d...
```

The attacker just looks up any stolen hash in their precomputed table — instant crack.

With a unique salt per user, precomputed tables don't work because the attacker would need to precompute one table per user. bcrypt's random salt makes this essentially impossible.

---

## The Login Flow: Step by Step

Here is exactly what happens when a user clicks "Sign in":

### In app.py:

```python
if submit:                               # user clicked the Sign in button
    user_info = check_login(username, password)   # call auth/auth.py
    if user_info:
        st.session_state.authenticated = True     # mark as logged in
        st.session_state.user_info = user_info    # store their info
        init_session_tracking()                   # start session timer
        issue_session_token(user_info['username']) # remember-me URL token
        st.rerun()                                # refresh the page
    else:
        st.error('Incorrect username or password.')  # same message for all failures
```

The `issue_session_token()` call is what lets users stay signed in across browser refreshes — see the section below.

### In auth/auth.py — check_login():

```
Step 1: Check if username or password fields are empty → return None

Step 2: check_login_rate_limit(username)
        → Has this username failed 5+ times in the last hour?
        → If yes: log RATE_LIMITED to audit_log table → return None
        → If no: continue

Step 3: load_users() from PostgreSQL
        → SELECT username, password_hash, display_name, customers, role FROM users
        → Returns a fresh dict, no caching

Step 4: Is the username in the users dict?
        → If not: record_failed_login(username)
                  log LOGIN_FAILED to audit_log table
                  run a dummy bcrypt verify (constant-time response)
                  → return None
        → If yes: continue

Step 5: verify_password(password, stored_hash)
        → bcrypt.checkpw(password.encode(), stored_hash.encode())
        → If fails: record_failed_login(username)
                    log LOGIN_FAILED to audit_log table
                    → return None

Step 6: Successful login!
        → reset_login_attempts(username)    ← clear their failed counter
        → log LOGIN_SUCCESS to audit_log table
        → return {username, display_name, customers, role}
```

---

## Persistent Login: Staying Signed In Across Refreshes

### The Problem

Streamlit stores `st.session_state` in **server memory**, keyed by the WebSocket connection. When a user hits the browser refresh button:

1. The browser tears down the existing WebSocket
2. Streamlit treats the reconnect as a brand-new session
3. `st.session_state.authenticated` is gone → the login form appears again
4. The user has to type their password every time they reload the page

This is jarring compared to normal web apps (Gmail, GitHub) where refresh just reloads the UI. We solve it with a signed **URL query parameter token**.

### Why Not Browser Cookies?

We initially tried browser cookies via the `extra-streamlit-components` library. Three problems made it unworkable:

1. `cookies.set()` and `cookies.delete()` are **async JavaScript messages** — `st.rerun()` fires before the browser actually writes the cookie, so set/delete frequently miss.
2. The CookieManager runs in a Streamlit component iframe. Firefox Private Browsing applies Total Cookie Protection that isolates iframe-set cookies from the main page jar, so the cookie is never sent back at all.
3. On every refresh, the component returns `None` for the first script run while it loads, causing a visible flash of the login form before auto-restore.

`st.query_params` is built into Streamlit, **synchronous**, available on the very first line of the script, and not subject to any of the above.

### How the Token Flow Works

```
                ┌─────────────────────────────────────────┐
                │  User submits username + password       │
                └────────────────────┬────────────────────┘
                                     │
                                     ▼
                ┌─────────────────────────────────────────┐
                │  check_login() verifies bcrypt hash     │
                └────────────────────┬────────────────────┘
                                     │ success
                                     ▼
                ┌─────────────────────────────────────────┐
                │  issue_session_token(username)          │
                │  → token = username|expiry|HMAC-SHA256  │
                │  → written to URL as ?s=<token>         │
                │  → st.rerun() loads the new URL         │
                └─────────────────────────────────────────┘

       ────────────── later, user hits browser refresh ──────────────

                ┌─────────────────────────────────────────┐
                │  Browser reloads the same URL — token   │
                │  is still in the query string           │
                └────────────────────┬────────────────────┘
                                     │
                                     ▼
                ┌─────────────────────────────────────────┐
                │  try_restore_session() reads             │
                │  st.query_params["s"] on line 1         │
                │  → recompute HMAC with SESSION_SECRET   │
                │  → compare with constant-time check     │
                └────────────────────┬────────────────────┘
                                     │ valid + not expired
                                     ▼
                ┌─────────────────────────────────────────┐
                │  Fetch fresh role/customer from DB       │
                │  (so demoted users do not keep old      │
                │  privileges)                            │
                │  → populate st.session_state            │
                │  → user lands on the chat page          │
                │     directly, with NO login-form flash  │
                └─────────────────────────────────────────┘
```

### The Token Format (Unchanged from the Cookie Version)

The query parameter value is a three-part string joined with `|`:

```
?s=admin|1716800000|7f3a1b9e2d4c8a6f5e3d2c1b9a8e7f6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a09
   └─┬─┘ └────┬───┘ └──────────────────────────────────────────────┬─────────────┘
   username  unix-expiry                                       HMAC-SHA256 signature
```

The signature is computed as `HMAC-SHA256(secret, "username|expiry")`. Without knowing the secret, no one can:

- Forge a token for another username (signature would not match)
- Extend their own expiry (any change invalidates the signature)
- Inject a fake admin user (same reason)

If anyone tampers with even one character, `hmac.compare_digest()` rejects the token and the user is bounced to the login form.

### Why We Re-fetch From the Database

The token only proves "this browser logged in as user X at some point". It does NOT carry the user's role or customer list — those are looked up fresh from the `users` table on every page load:

```python
# auth/session_token.py — try_restore_session()
user_info = get_user_info(username)   # fresh DB read, no cache
if not user_info:
    clear_session_token()              # user was deleted → revoke token
    return False
```

This means:
- If an admin demotes someone from `admin` to `sre`, the demotion takes effect on the very next page load — even though the token is still valid.
- If an admin deletes a user, their token stops working immediately.
- The token is a **convenience for skipping the login form**, not a privilege grant.

### The SESSION_SECRET Environment Variable

The signing key lives in `.env`:

```bash
SESSION_SECRET=9767cfb3db9ce95b71d31b88f6ef21d095e41a0cc23cb78f167f76b5614b57fb
```

Generate one with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Properties:
- **Treat it like a database password.** Anyone with the secret can forge tokens for any user.
- **Never commit it to git** — `.env` should be in `.gitignore`.
- **Rotating it logs everyone out once** (existing tokens fail signature check). That is the safe response if you suspect it leaked.
- **If the variable is missing**, `session_token.py` generates an ephemeral random key at startup and prints a warning. The app still works, but everyone gets logged out on container restart.

### Token Lifetime & What It Does NOT Do

| | |
|---|---|
| Token lifetime | 7 days (configurable via `TOKEN_LIFETIME_DAYS` in `auth/session_token.py`) |
| Survives browser refresh | ✓ |
| Survives closing the browser | Only if the URL is bookmarked |
| Survives container restart | ✓ (as long as SESSION_SECRET is stable) |
| Overrides 60-min inactivity timeout | ✗ — `check_session_timeout()` still runs |
| Overrides 8-hour max duration | ✗ — same |
| Stops working on Sign out | ✓ — `logout_user()` calls `clear_session_token()` |
| Stops working when user is deleted | ✓ — `get_user_info()` returns None, token is cleared |

The two session-timeout limits (60-min idle, 8-hour total) are **the security envelope**. The token just removes the friction of typing the password every refresh inside that envelope.

### Security Caveat: URL Sharing

Because the token lives in the URL, **anyone you give your full URL to (copy-paste, screenshot of address bar, etc.) is auto-logged-in as you** until the token expires. For this internal tool used by trusted WSO2 engineers on HTTPS, this is the same trust model as "don't share your password." If you ever need to share a URL with a colleague, strip the `?s=...` portion first, or send them just the base host.

### Files Involved

| File | Role |
|---|---|
| `auth/session_token.py` | The whole token module: signing, verifying, issuing, clearing |
| `auth/auth.py` | `get_user_info(username)` helper used during restore |
| `app.py` | Calls `try_restore_session()` before showing login; calls `issue_session_token()` after successful login |
| `auth/auth_guard.py` | Calls `try_restore_session()` so dashboard pages also restore on refresh |
| `auth/session_manager.py` | `logout_user()` now clears the token alongside session state |
| `.env` | Holds `SESSION_SECRET` |

---

## Security Detail: Constant-Time Response

When someone types a username that doesn't exist, we still run a fake bcrypt verification:

```python
# From auth/auth.py:
if username not in users:
    record_failed_login(username)
    log_security_event(LOGIN_FAILED, ...)
    # Still run a dummy verify to maintain constant response time
    verify_password(password, "$2b$12$dummyhashfornon.existentuserXXXXXXXXXXXXXXXXXXXXXXXX")
    return None
```

**Why?** Without this, an attacker could measure how long the login takes:
- Wrong username → returns in 1ms (no hash computation)
- Right username, wrong password → returns in 100ms (bcrypt ran)

From timing alone, the attacker knows which usernames are valid. By always running bcrypt (even for fake hashes), both cases take ~100ms — the attacker learns nothing from timing.

---

## How auth/auth_guard.py Protects Dashboard Pages

Every dashboard page (Evaluation, Usage, Admin, Ingestion) starts with:

```python
from auth.auth_guard import require_authentication
user_info = require_authentication()
```

`require_authentication()` in auth/auth_guard.py does:

```python
def require_authentication():
    # 1. Try to restore session from the remember-me cookie
    #    (so a refresh on a dashboard page does not bounce the user)
    try_restore_session()

    # 2. Still not logged in? Show "Access Denied" and st.stop()
    if not st.session_state.authenticated:
        st.warning('🔒 Access Denied — Authentication Required')
        st.stop()

    # 3. Session expired? Log out and st.stop()
    session_valid, message = check_session_timeout()
    if not session_valid:
        logout_user()
        st.stop()

    # 4. All good — show the logout button in sidebar and return user_info
    return st.session_state.user_info
```

Because `st.stop()` halts all further execution, no page content is ever rendered for unauthenticated or expired sessions. The user sees only the "Access Denied" message.

---

## Role-Based Access Control

The system has three roles:

| Role | Can Access Chat | Can Access Dashboards | Can Access Admin Panel |
|------|----------------|----------------------|----------------------|
| `sre` | Yes | Yes | No |
| `senior_sre` | Yes | Yes | No |
| `admin` | Yes | Yes | Yes |

The Admin Panel check in `pages/5_Admin_Panel.py`:

```python
user_info = require_authentication()   # must be logged in

if user_info.get('role') != 'admin':   # must be admin role
    st.error('🔒 Admin access required')
    st.stop()
```

---

## How Passwords Are Created for New Users

When an admin adds a new user in the Admin Panel:

```python
# pages/5_Admin_Panel.py
success = create_user(
    username=new_username.lower().strip(),
    password=new_password,          # plain text from the form
    display_name=new_display,
    role=new_role
)
```

Inside `auth/auth.py create_user()`:

```python
# 1. Hash the password with bcrypt IMMEDIATELY
password_hash = hash_password(password)
# → password is never stored, only the hash goes into the database

# 2. INSERT into the users table
with get_db() as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, display_name, customers, role)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            """,
            (username, password_hash, display_name, ['ALL'], role)
        )
```

The plain-text password exists only for a fraction of a second — just long enough to pass it to bcrypt. After that, only the hash exists.

---

## Why Users Are Read Fresh on Every Login

```python
def load_users() -> dict:
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username, password_hash, display_name, customers, role FROM users")
            rows = cur.fetchall()
    return {row[0]: {...} for row in rows}
```

There is no caching. Every login attempt issues a fresh SELECT. This means:
- An admin can add or remove a user in the Admin Panel
- The change takes effect **immediately** — the next login attempt sees the updated table
- No app-container restart needed (and the postgres container keeps running independently)

The connection helper `db.py` pools PostgreSQL connections so the per-login cost is just a query, not a new TCP/handshake.

---

## Historical Notes (No Longer Active)

- `auth.py.sha256.backup` — the old SHA-256 version of `auth.py`, removed in the bcrypt migration
- `scripts/migration.py` — one-time script that re-hashed all passwords from SHA-256 to bcrypt
- `users.json` — the pre-PostgreSQL user store (migration recorded in `docs/migrateforpostgresql.md`)
- `auth/cookie_auth.py` — the pre-URL-token persistent-login implementation (removed, see `docs/url_token_session_upgrade.md`)

All current rows in the `users` table store bcrypt hashes (they start with `$2b$`).
