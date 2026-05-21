# 05 — Security: Rate Limits, Sessions, Audit Logs, and HTTPS

> Four layers of protection explained from basic concepts to implementation details.

---

## Overview: The Four Security Layers

```
Layer 1: HTTPS Transport    → encrypts data between browser and server
Layer 2: Authentication     → proves who the user is (covered in doc 04)
Layer 3: Session Management → limits how long a session lasts
Layer 4: Rate Limiting      → limits how fast a user can act
                              ↓
Layer 5 (logging): Audit Log → records everything for review
```

All of these work together. Even if one layer fails, others are still protecting the system.

---

## Layer 1: HTTPS (Transport Security)

### What Is HTTPS?

HTTP (HyperText Transfer Protocol) is the language browsers use to talk to servers. By default, it sends everything as plain text.

HTTPS is HTTP over TLS (Transport Layer Security) — a protocol that encrypts the connection. Everything sent between the browser and server is scrambled and can only be read by the two endpoints.

### Why It Matters for This App

Without HTTPS:
- A colleague on the same Wi-Fi network could run a packet sniffer and see every question you type
- They could see the AI's answer and the source documents cited
- They could capture your username and password during login

With HTTPS:
- All traffic looks like random bytes to anyone intercepting it
- Only the browser and server can decrypt it

### How Our HTTPS Is Set Up

We have TLS certificates in `certs/`:
```
certs/cert.pem   ← the public certificate (who we are)
certs/key.pem    ← the private key (never share this)
```

The app is started with:
```bash
streamlit run app.py \
  --server.sslCertFile=certs/cert.pem \
  --server.sslKeyFile=certs/key.pem
```

Streamlit's built-in server handles the TLS handshake. When a browser connects, it receives `cert.pem` to verify the server's identity, then negotiates an encrypted channel using the asymmetric key pair.

### The TLS Handshake (Simplified)

```
Browser:  "Hello server, I support these encryption methods: [list]"
Server:   "Here is my certificate. Let's use AES-256 encryption."
Browser:  "Certificate verified. Here is a random session key, encrypted with your public key."
Server:   (decrypts session key using private key)
Both:     "Now all traffic is encrypted with the session key."
```

After this, every byte going both ways is encrypted. The session key is unique per connection and thrown away when the session ends.

---

## Layer 3: Session Management (auth/session_manager.py + auth/session_token.py)

### The Problem Sessions Solve

Once you log in, how does the server know you're still you on the next page load? HTTP is stateless — every request is independent.

Streamlit solves this with `st.session_state` — a dictionary stored in server memory, associated with your browser tab. Our code stores the authentication state there.

`st.session_state` is wiped on browser refresh (each refresh opens a new WebSocket, which Streamlit treats as a fresh session). To avoid forcing users to retype their password every refresh, we also keep a signed token in the URL query string (`?s=...`); `auth/session_token.py` reads it on every script run and restores the session state. The token is **HMAC-SHA256 signed** with `SESSION_SECRET` from `.env`, so it cannot be forged. Full details in `04_authentication.md` and `url_token_session_upgrade.md`.

But we also need to handle two scenarios:
1. **User walks away from their computer** — the session should eventually expire
2. **User keeps the tab open all day** — we force re-login periodically for security

### The Two Timeout Checks

Every page load (every rerun) calls `check_session_timeout()` which does two checks:

#### Check 1: Inactivity Timeout (60 minutes)

```python
time_since_activity = now - st.session_state.last_activity

if time_since_activity > timedelta(minutes=60):
    # Session expired — user was inactive for 60+ minutes
    return False, "Your session expired after X minutes of inactivity."
```

Every valid page load updates `last_activity = now`. So if you're actively using the app (clicking buttons, submitting queries), the timer keeps resetting. You only get logged out if you stop interacting for 60 minutes straight.

#### Check 2: Maximum Duration (8 hours)

```python
session_duration = now - st.session_state.session_start

if session_duration > timedelta(hours=8):
    # Session expired — user has been logged in for 8+ hours
    return False, "Maximum 8-hour session reached."
```

Even if someone clicks every minute for 8 hours, they still get logged out. This limits the damage from a stolen browser session — at most 8 hours of access.

### What Happens on Session Expiry

```python
# From app.py:
session_valid, timeout_message = check_session_timeout()

if not session_valid:
    st.warning(timeout_message)           # show the expiry message
    logout_user()                         # clear all session state
    # show "Click here to log in again" button
    st.stop()                             # stop rendering the page
```

`logout_user()` clears:
- `st.session_state.authenticated` → False
- `st.session_state.user_info` → None
- `st.session_state.messages` → [] (chat history gone)
- `st.session_state.last_activity` → deleted
- `st.session_state.session_start` → deleted

After `logout_user()`, the next rerun will show the login form.

---

## Layer 4: Rate Limiting (auth/rate_limiter.py)

Rate limiting controls how fast a user can perform actions. We have two separate rate limiters.

### Rate Limiter 1: Query Rate Limiting

This protects the Gemini API from being hammered.

**Limits:**
- 10 queries per minute per user
- 100 queries per hour per user

**Mechanism — Sliding Window:**

Instead of a fixed 1-minute window (like a counter that resets at :00 of every minute), we use a sliding window. This is more accurate and fairer.

```python
_query_timestamps: dict = defaultdict(list)
# This stores a list of timestamps for each user
# e.g., {'alice': [datetime(10:01:05), datetime(10:01:20), ...]}

def check_query_rate_limit(username):
    now = datetime.now()
    
    # Step 1: Clean up old timestamps (older than 1 hour)
    _query_timestamps[username] = [
        ts for ts in _query_timestamps[username]
        if now - ts < timedelta(hours=1)
    ]
    
    # Step 2: Count timestamps in the last 60 seconds
    recent_minute = [ts for ts in _query_timestamps[username]
                     if now - ts < timedelta(minutes=1)]
    
    # Step 3: Check limits
    if len(recent_minute) >= 10:
        return False, "Rate limit: wait 60 seconds"
    
    if len(_query_timestamps[username]) >= 100:
        return False, "Hourly limit reached"
    
    # Step 4: Record this query
    _query_timestamps[username].append(now)
    return True, ""
```

**Example:**
- Alice sends 10 queries between 10:01:00 and 10:01:30
- At 10:01:31, she tries an 11th query → blocked (10 in last 60 seconds)
- At 10:02:01, she tries again → first query from 10:01:00 is now older than 60 seconds → window slides forward → 9 in last 60 seconds → allowed

**Important:** These counters are stored **in memory** (not in a file). They reset when the server restarts. This is fine for an internal tool.

### Rate Limiter 2: Login Rate Limiting

This prevents brute-force password attacks.

**Limit:** 5 failed login attempts per hour per username

```python
_failed_login_timestamps: dict = defaultdict(list)

def check_login_rate_limit(username):
    now = datetime.now()
    
    # Clean up timestamps older than 1 hour
    _failed_login_timestamps[username] = [
        ts for ts in _failed_login_timestamps[username]
        if now - ts < timedelta(hours=1)
    ]
    
    # If 5 or more failures in last hour → block
    if len(_failed_login_timestamps[username]) >= 5:
        return False, "Too many failed attempts. Wait 1 hour."
    
    return True, ""
```

**Critical:** The rate limit check happens **before** password verification:

```
Login attempt arrives
  │
  ▼
check_login_rate_limit()    ← FIRST CHECK
  │ blocked? → stop here, don't even check password
  │ allowed? → continue
  ▼
load_users() + verify_password()
  │ wrong password? → record_failed_login() → add timestamp to _failed_login_timestamps
  │ right password? → reset_login_attempts() → clear _failed_login_timestamps[username]
  ▼
return result
```

**Why check rate limit first?** Because each wrong password attempt runs bcrypt (~100ms). If we didn't check first, an attacker could spam the login form and just wait out the bcrypt slowdown on each attempt. By blocking before bcrypt, failed attempts become near-instant to reject.

### After a Successful Login

When login succeeds, we clear the failed attempt counter:

```python
reset_login_attempts(username)
# sets _failed_login_timestamps[username] = []
```

This way, a user who accidentally mistyped their password 4 times can still log in successfully, and their counter is reset — they start fresh next time.

---

## Layer 5 (Logging): Audit Log (monitoring/audit_log.py)

The audit log records every security-relevant event. It answers "who did what and when?"

Storage: events are written to the `audit_log` table in PostgreSQL (previously this was a flat `audit_log.json` file — see `docs/migrateforpostgresql.md` for the migration record).

### What Gets Logged

```python
# Event type constants:
LOGIN_SUCCESS    # user logged in successfully
LOGIN_FAILED     # wrong password or wrong username
LOGOUT           # user clicked "Sign out"
SESSION_EXPIRED  # session timed out
USER_CREATED     # admin added a new user
USER_DELETED     # admin removed a user
QUERY_EXECUTED   # user ran a RAG query
RATE_LIMIT_HIT   # user hit a rate limit
```

### Table Schema

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type  TEXT NOT NULL,
    username    TEXT NOT NULL,
    ip_address  TEXT,
    success     BOOLEAN NOT NULL DEFAULT TRUE,
    details     JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_audit_timestamp  ON audit_log(timestamp);
CREATE INDEX idx_audit_username   ON audit_log(username);
CREATE INDEX idx_audit_event_type ON audit_log(event_type);
```

### Why PostgreSQL Instead of JSON

The old JSON approach used a "write-then-rename" atomic pattern to avoid corruption. PostgreSQL gives us this for free via transactions — plus:

- Concurrent writers cannot corrupt each other (the JSON file struggled under multiple containers)
- Indexed queries (e.g. "all LOGIN_FAILED events in the last hour") are fast even with millions of rows
- The `details` field uses `JSONB`, which is queryable with standard SQL operators

Same shape of record as before, just queryable with SQL instead of `json.load()`.

### Audit Log Use Cases

**Detecting brute force:**
```python
recent_failures = get_failed_logins_last_n_minutes(60)
# Returns list of LOGIN_FAILED events in the last 60 minutes
# If you see 50 failures for "alice" in 10 minutes → her account is under attack
```

**User activity trail:**
```python
trail = get_user_audit_trail('alice', limit=50)
# Returns the 50 most recent events for alice
# Useful if you need to know: did alice run queries yesterday?
```

---

## The Query Log (monitoring/logger.py)

Separate from the audit log, the `query_log` table in PostgreSQL records operational data about every AI query:

```sql
CREATE TABLE query_log (
    id             BIGSERIAL PRIMARY KEY,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    username       TEXT NOT NULL,
    question       TEXT,
    customer_scope TEXT NOT NULL DEFAULT 'ALL',
    answer_length  INTEGER NOT NULL DEFAULT 0,
    num_sources    INTEGER NOT NULL DEFAULT 0,
    latency_ms     INTEGER NOT NULL DEFAULT 0,
    success        BOOLEAN NOT NULL DEFAULT TRUE,
    error          TEXT,
    top_source     TEXT
);
```

This powers the Usage Dashboard (page 4):
- How many queries per day?
- Which users ask the most?
- What is the average response time?
- Which documents are retrieved most often?

The query log is for **operational metrics**, not security. The audit log is for **security events**.

---

## Summary: What Protects Against What

| Threat | Protection |
|--------|-----------|
| Eavesdropping on network | HTTPS/TLS encryption |
| Guessing weak passwords | bcrypt slow hashing |
| Trying many passwords | Rate limiter (5 attempts/hour) |
| Knowing which usernames exist | Constant-time response for invalid users |
| Precomputed hash tables | bcrypt salts (unique per user) |
| Abandoned logged-in sessions | 60-minute inactivity timeout |
| All-day session hijacking | 8-hour maximum session limit |
| API cost explosion | 10 queries/min, 100 queries/hour limits |
| Unnoticed attacks | Audit log records all security events |
| Unauthorized page access | auth/auth_guard.py on every page |
| Admin-only actions by non-admins | Role check in Admin Panel |
| Login flash + manual re-login on every refresh | Signed URL-token persistent login (see `04_authentication.md` and `url_token_session_upgrade.md`) |
