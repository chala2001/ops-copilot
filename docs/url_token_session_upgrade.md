# URL-Token Authentication & How the Session Limits Behave

> A complete record of the recent auth upgrade: what we changed, why we changed it, and exactly what happens to every timer when a user refreshes the browser.

---

## 1. The Upgrade in One Sentence

We replaced **browser-cookie-based "remember me"** (using `extra-streamlit-components`) with **URL-query-parameter-based "remember me"** (using Streamlit's built-in `st.query_params`).

The signing logic, security model, user table, role checks, and timeout policies are **completely unchanged**. Only the place where the session token lives changed: from a browser cookie to the page URL.

---

## 2. Why We Replaced Cookies

The cookie approach failed in production for three independent reasons:

### Problem A — Async cookie operations vs. synchronous `st.rerun()`

`extra-streamlit-components.CookieManager.set()` and `.delete()` work by sending a message to a JavaScript iframe that then calls `document.cookie = ...`. The Python side returns immediately, but the actual cookie write happens **after** the function returns.

Our login flow looked like:

```python
issue_session_cookie(user_info['username'])   # queues a JS message
st.rerun()                                    # halts the script
```

`st.rerun()` killed the script before the browser had a chance to write the cookie. Sometimes the cookie was set, often it wasn't. We added `time.sleep(0.5)` as a band-aid, but it was unreliable.

### Problem B — Iframe isolation in Firefox Private Browsing

Streamlit custom components render inside an iframe. Firefox Private Browsing applies **Total Cookie Protection**, which isolates iframe-set cookies from the main page's cookie jar — even when the iframe is on the same origin.

The diagnostic logs proved this: only Streamlit's own server-set `_streamlit_xsrf` cookie ever appeared. Our `ops_copilot_session` cookie was never sent back by the browser, no matter how many sleeps we added.

### Problem C — Login-form flash on every refresh

On a browser refresh, the cookie component returned `None` for the first script run (the JS hadn't sent its data back yet). So the script rendered the login form, then the component triggered an automatic rerun, then the second run found the cookie and restored the session. The user saw a 100–300 ms flash of the login form every single time.

---

## 3. What URL Query Parameters Give Us

| Property | Cookie approach | URL-token approach |
|---|---|---|
| API call | `extra-streamlit-components` (third-party) | `st.query_params` (built-in) |
| Sync or async | Async (JS message) | Synchronous |
| Available on line 1 of the script | No (returns `None` first) | Yes |
| Iframe involved | Yes | No |
| Works in Private Browsing | No (Firefox blocks it) | Yes |
| Sign-out reliability | Needs `time.sleep` band-aid | Synchronous deletion, no delay needed |
| Refresh flash | Always present | None |
| Lines of code | ~140 | ~120 |
| Token visible to user | No | Yes (in URL bar) |

The single trade-off is the last row: the token is visible in the URL. Mitigations and security implications below.

---

## 4. How the Token Itself Works (Same as Before)

```
?s=admin|1716800000|7f3a1b9e2d4c8a6f5e3d2c1b9a8e7f6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a09
   └─┬─┘ └────┬───┘ └──────────────────────────────────────────────┬─────────────┘
   username  unix-expiry                                       HMAC-SHA256 signature
```

The token is a three-part string joined with `|`:

1. **Username** — plain text
2. **Expiry timestamp** — Unix seconds, set to `login_time + 7 days`
3. **HMAC-SHA256 signature** — `HMAC(SESSION_SECRET, "username|expiry")`

To **forge** a token, an attacker would need the `SESSION_SECRET` from `.env`. Without it, any tampering (changing username, extending expiry) invalidates the signature and the token is rejected.

The verification is constant-time (`hmac.compare_digest`) so signature comparison cannot be timing-attacked.

---

## 5. The Full Flow

### On Login

```
User submits username + password
        │
        ▼
check_login() verifies bcrypt hash, checks rate limiter, logs audit event
        │
        ▼   (success)
session_state.authenticated = True
session_state.user_info = {...}
init_session_tracking()                   # records session_start = now
                                          # records last_activity = now
issue_session_token(username)             # writes ?s=token to URL
                                          # synchronous, no delay needed
st.rerun()                                # loads the chat page
```

### On Browser Refresh

```
Browser reloads https://localhost:8501/?s=admin|...|...
        │
        ▼
Streamlit starts a fresh script run with empty session_state
        │
        ▼
try_restore_session() reads st.query_params["s"]
        │
        ▼
_verify_token() recomputes HMAC and compares
        │
        ▼   (valid + unexpired)
get_user_info(username) → fresh DB read for role/customers
        │
        ▼
session_state.authenticated = True
session_state.user_info = {...}
session_state.session_start = (expiry - 7 days)     ← original login time
session_state.last_activity = now                    ← refresh = activity
        │
        ▼
Script continues to the main app — NO login-form flash
```

### On Page Navigation (Sidebar Click)

Streamlit's sidebar links **strip query parameters** when navigating between pages. Without intervention, clicking "Admin Panel" would change the URL from `/?s=token` to `/Admin_Panel` (token dropped). On the dashboard page, a refresh would then have nothing to restore from.

We work around this in `try_restore_session()`:

```python
if st.session_state.get('authenticated'):
    if QUERY_PARAM not in st.query_params:
        # Streamlit just dropped our token in a page nav — re-stamp it
        issue_session_token(st.session_state.user_info['username'])
    return True
```

So every page write the token back into the URL if it's missing. The user sees `/Admin_Panel?s=token` after a fraction of a second.

### On Sign Out

```
User clicks Sign out
        │
        ▼
logout_user() clears session_state (authenticated, user_info, timestamps)
        │
        ▼
clear_session_token() deletes ?s= from the URL — synchronous
        │
        ▼
st.rerun()
        │
        ▼
Fresh run: URL has no token, session_state is empty → login form
```

No `time.sleep` band-aid required because `del st.query_params['s']` updates the URL immediately.

---

## 6. Files Involved

| File | Purpose |
|---|---|
| `auth/session_token.py` | Token signing, verification, issuance, clearing |
| `auth/auth.py` | `get_user_info(username)` helper used during restore |
| `auth/auth_guard.py` | Calls `try_restore_session()` on every dashboard page |
| `auth/session_manager.py` | `logout_user()` calls `clear_session_token()` |
| `app.py` | Calls `try_restore_session()` at top; `issue_session_token()` after login |
| `.env` | Holds `SESSION_SECRET` |
| **Removed:** `auth/cookie_auth.py` | The old cookie module — deleted |
| **Removed from `requirements.txt`** | `extra-streamlit-components` — no longer needed |

---

## 7. How Each Timer Behaves Around a Refresh

This is the part most people get confused about. Here's the **exact** behavior, with the recent bug fix applied.

### 7.1 The 60-Minute Inactivity Timer

Defined in `auth/session_manager.py`:

```python
SESSION_TIMEOUT_MINUTES = 60
```

**What it does**: if a user has not interacted with the app for 60 minutes, they are logged out.

**What counts as "interaction"**: any Streamlit rerun — every button click, form submit, chat message, page navigation, **and a browser refresh**. On every rerun, if the session is still valid, `last_activity` is updated to `now`.

**Behavior on browser refresh**:
- `last_activity` is **reset to now** ✓ (this is correct — the user just interacted)
- They get a full fresh 60-minute window of inactivity tolerance from this moment

**Why this is correct**: if you walk away for 59 minutes, come back, refresh the page, you're still in. If you walk away for 61 minutes, come back, refresh — you're logged out because `check_session_timeout()` runs **before** `last_activity` is updated, sees the 61-minute gap, and ejects you.

### 7.2 The 8-Hour Max Duration Timer

Defined in `auth/session_manager.py`:

```python
SESSION_MAX_DURATION_HOURS = 8
```

**What it does**: even if a user is actively clicking buttons all day, they are forced to log in again 8 hours after the original login. This protects against laptop theft and abandoned sessions.

**Behavior on browser refresh** (after the fix):
- `session_start` is **NOT reset to now**
- Instead, the original login time is **derived from the token's expiry**: `session_start = expiry_unix - 7*86400`
- The 8-hour clock keeps counting from the real login moment

**Worked example**:
- You log in at 09:00 → token expires at 09:00 next-week-Friday → `session_start = 09:00 today`
- At 13:00 you refresh → session_state is wiped, restored from token → `session_start` is set back to 09:00, not 13:00
- At 17:01 you do anything → `now - session_start = 8h 01min` → forced logout ✓

**Before the fix** (just patched): every refresh reset `session_start` to "now", so a user who refreshed every 7 hours could stay logged in forever. That's no longer possible.

### 7.3 The 7-Day Token Expiry

Defined in `auth/session_token.py`:

```python
TOKEN_LIFETIME_DAYS = 7
```

**What it does**: after 7 days from login, the token expires and the user has to log in again, even if they were never logged out by the 8-hour rule.

**Behavior on browser refresh**: nothing — the token's expiry is fixed at login time. It does **not** slide forward on each refresh.

**Realistic interaction**: in practice, the 8-hour rule fires first (once a day), so the 7-day expiry only matters if a user is genuinely inactive for a long time but their token is still in their URL history.

### 7.4 Summary Table

| Timer | Where it lives | Resets on refresh? | What triggers logout |
|---|---|---|---|
| 60-min inactivity | `session_state.last_activity` | Yes (refresh counts as activity) | No interaction for 60 min |
| 8-hour max duration | `session_state.session_start` (derived from token expiry) | **No** (fixed at original login) | 8 hours since login, regardless of activity |
| 7-day token expiry | Inside the URL token | No | 7 days since login, regardless of activity |
| Sign out | All of the above are cleared | n/a | User clicks the button |

---

## 8. How the Rate Limiter Behaves Around a Refresh

Defined in `auth/rate_limiter.py`. Uses an **in-memory sliding window** — timestamps are kept in Python `dict` structures inside the running process.

### 8.1 The Three Limits

| Limit | Constant | Value | Purpose |
|---|---|---|---|
| Queries per minute | `MAX_QUERIES_PER_MINUTE` | 10 | Prevents copy-paste loops or runaway scripts |
| Queries per hour | `MAX_QUERIES_PER_HOUR` | 100 | Caps sustained API costs |
| Failed logins per hour | `MAX_LOGIN_ATTEMPTS_PER_HOUR` | 5 | Slows down brute-force attacks |

### 8.2 Storage Location

```python
_query_timestamps: dict = defaultdict(list)        # username → [datetime, datetime, ...]
_failed_login_timestamps: dict = defaultdict(list) # username → [datetime, ...]
```

These are **module-level dicts inside the running container**. Key consequences:

- They are **not** in Streamlit's session state
- They are **not** in PostgreSQL
- They survive across Streamlit reruns
- They survive across browser refreshes
- They survive across sign-out / sign-in
- **They reset on container restart** (`docker compose restart app`)

### 8.3 Behavior on Browser Refresh

**Refreshing the browser does NOT reset rate limit counters**, because counters are keyed by **username**, not by Streamlit session.

Worked example:
1. User `alice` asks 9 questions → her per-minute count is 9
2. Alice hits F5 → fresh Streamlit session, but `_query_timestamps['alice']` still contains those 9 timestamps
3. Alice asks one more question → count is 10 → still allowed
4. Alice asks an 11th question → blocked with "rate limit reached"

This is correct behavior — rate limits should protect against the user, not against the session.

### 8.4 The Sliding Window

On every check, `check_query_rate_limit()` cleans timestamps older than 1 hour:

```python
_query_timestamps[username] = [
    ts for ts in _query_timestamps[username]
    if now - ts < timedelta(hours=1)
]
```

Then counts:
- Last 1 minute → vs. `MAX_QUERIES_PER_MINUTE`
- Last 1 hour → vs. `MAX_QUERIES_PER_HOUR`

So if Alice hits her per-minute limit, she's blocked until the oldest of her 10 timestamps falls out of the minute window. She doesn't have to wait a full minute from the block — only until one of her recent queries ages out.

### 8.5 Failed Login Lockout

Same mechanism, but the counters are written on **failed** attempts and **cleared on success**:

```python
record_failed_login(username)    # on wrong password
reset_login_attempts(username)   # on correct password
```

So:
- 5 wrong passwords in a row → locked out for 1 hour
- 4 wrong, then 1 right → counter wiped, no lockout
- Lockout persists across refresh / new browser / new IP — anyone trying that username waits an hour

### 8.6 Important Caveat: Container Restart Wipes Limiters

Because `_query_timestamps` and `_failed_login_timestamps` are in process memory, restarting the container (`docker compose restart`, `docker compose down/up`, etc.) wipes all rate-limit history. A user who was 9/10 on the minute window becomes 0/10 again.

For a 50-user internal tool this is acceptable. If we ever needed durable rate limits (public-facing, regulatory requirement, etc.), the right fix would be to move the counters into PostgreSQL or Redis.

---

## 9. The Combined Picture: What a Day Looks Like

Pretend Alice logs in at 09:00 and uses the app throughout the day.

| Time | Event | What happens to each timer |
|---|---|---|
| 09:00 | Logs in | `session_start = 09:00`, `last_activity = 09:00`, token expires 09:00 next-week-Friday |
| 09:05 | Asks 5 questions | `last_activity → 09:05`, query counter has 5 entries |
| 10:00 | Quiet hour | `last_activity` still 09:05 |
| 10:30 | Refreshes browser | session_state wiped, restored from URL token → `session_start = 09:00` (from token), `last_activity = 10:30` |
| 12:00 | At lunch, walks away | No activity for the next hour |
| 13:30 | Comes back, refreshes | **Logged out** — `now - last_activity = 60+ min`, inactivity timeout fires *before* refresh counts as activity |
| 13:31 | Logs in again | New `session_start = 13:31`, new token issued |
| 17:30 | Asks 11 questions in a minute | First 10 succeed, 11th blocked by per-minute limit |
| 17:31 | Tries again | If a 1-minute-old query has aged out, allowed; otherwise still blocked |
| 21:30 | Refreshes | **Logged out** — 8 hours since 13:31 login |

---

## 10. Quick Reference

```bash
# Generate a fresh SESSION_SECRET (do this only if you need to rotate)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Configurable values
auth/session_manager.py:  SESSION_TIMEOUT_MINUTES     = 60
auth/session_manager.py:  SESSION_MAX_DURATION_HOURS  = 8
auth/session_token.py:    TOKEN_LIFETIME_DAYS         = 7
auth/rate_limiter.py:     MAX_QUERIES_PER_MINUTE      = 10
auth/rate_limiter.py:     MAX_QUERIES_PER_HOUR        = 100
auth/rate_limiter.py:     MAX_LOGIN_ATTEMPTS_PER_HOUR = 5
```

## 11. Security Caveat: URL Sharing

The token is in the URL. If a user copies their full URL and shares it (Slack, email, screenshot of the address bar), the recipient is auto-logged-in **as that user** for up to 7 days.

For this internal-only tool used by trusted WSO2 engineers over HTTPS, this is the same trust model as "don't share your password." If you need to share a link with a colleague, strip the `?s=...` portion first or send only the base URL.

If you ever expose this app to less-trusted users, switch back to a server-side session store (PostgreSQL-backed `sessions` table keyed by an opaque random ID, with the random ID stored in the URL instead of the full signed payload). The opaque-ID approach is what frameworks like Django and Rails use by default.
