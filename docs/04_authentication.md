# 04 — Authentication: Login, Passwords, and How It All Works

> From "user types password" to "user is logged in" — every step explained at the deepest level.

---

## The Big Picture

Authentication answers the question: **"Who are you, and can I trust that you are who you say you are?"**

Our system uses a username + password login. The password is never stored as plain text anywhere. Instead, it is stored as a bcrypt hash in `users.json`. When someone logs in, we verify their password against the stored hash.

---

## Where User Data Lives: users.json

```json
{
  "users": {
    "alice": {
      "password_hash": "$2b$12$4fzFhO.q8el8cASDithqFeAU0EO5Cjg76G7NdMKpp27J1QYEYMuve",
      "display_name": "Alice (Senior SRE)",
      "customers": ["ALL"],
      "role": "senior_sre"
    },
    "admin": {
      "password_hash": "$2b$12$NEMkyADvvMZMllCkkE/yVeTdwAS0G1pj64h2gC9.JJer62ltflrd6",
      "display_name": "Admin",
      "customers": ["ALL"],
      "role": "admin"
    }
  }
}
```

Notice:
- **No plain-text password anywhere** — only `password_hash`
- `customers: ["ALL"]` means this user can search all documents
- `role` controls what pages they can access (e.g., only `admin` can open the Admin Panel)

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
        st.rerun()                                # refresh the page
    else:
        st.error('Incorrect username or password.')  # same message for all failures
```

### In auth/auth.py — check_login():

```
Step 1: Check if username or password fields are empty → return None

Step 2: check_login_rate_limit(username)
        → Has this username failed 5+ times in the last hour?
        → If yes: log RATE_LIMITED to audit_log.json → return None
        → If no: continue

Step 3: load_users() from users.json
        → Read the JSON file fresh from disk (no caching)

Step 4: Is the username in the users dict?
        → If not: record_failed_login(username)
                  log LOGIN_FAILED to audit_log.json
                  run a dummy bcrypt verify (constant-time response)
                  → return None
        → If yes: continue

Step 5: verify_password(password, stored_hash)
        → bcrypt.checkpw(password.encode(), stored_hash.encode())
        → If fails: record_failed_login(username)
                    log LOGIN_FAILED to audit_log.json
                    → return None

Step 6: Successful login!
        → reset_login_attempts(username)    ← clear their failed counter
        → log LOGIN_SUCCESS to audit_log.json
        → return {username, display_name, customers, role}
```

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
    # 1. Not logged in? Show "Access Denied" and st.stop()
    if not st.session_state.authenticated:
        st.warning('🔒 Access Denied — Authentication Required')
        st.stop()
    
    # 2. Session expired? Log out and st.stop()
    session_valid, message = check_session_timeout()
    if not session_valid:
        logout_user()
        st.stop()
    
    # 3. All good — show the logout button in sidebar and return user_info
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
# → password is never stored, only the hash goes into users.json

# 2. Build the user record
users[username] = {
    'password_hash': password_hash,
    'display_name': display_name,
    'customers': ['ALL'],
    'role': role
}

# 3. Save to users.json
```

The plain-text password exists only for a fraction of a second — just long enough to pass it to bcrypt. After that, only the hash exists.

---

## Why users.json Is Read Fresh on Every Login

```python
def load_users() -> dict:
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['users']
```

There is no caching. Every login attempt reads the file fresh from disk. This means:
- An admin can add or remove a user in the Admin Panel
- The change takes effect **immediately** — the next login attempt will see the updated file
- No server restart needed

This is intentional. For a small team tool, the slight performance cost of a file read per login is negligible compared to the operational benefit of live user management.

---

## The SHA-256 Backup

You may notice `auth.py.sha256.backup` in the project. This is the old version of auth/auth.py that used SHA-256 instead of bcrypt. It's kept as a backup reference but is not used. All passwords in `users.json` are now bcrypt hashes (you can tell because they start with `$2b$`).

The migration from SHA-256 to bcrypt required recreating all passwords — the old SHA-256 hashes are not compatible with bcrypt verification.
