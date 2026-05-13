# STEP 4 — Audit Logging & Rate Limiting

## Why These Are Needed

### Audit Logging
Your current system logs queries to `query_log.json`, but there is no logging of
**security events**: logins, failed login attempts, logouts, or user management actions.

Without an audit trail you cannot:
- Detect that someone is brute-forcing a password
- Know who accessed the system and when during an incident
- Satisfy compliance requirements (SOC2, ISO27001 require access logs)
- Investigate "who changed X and when"

### Rate Limiting
Your current system has no limit on how many queries a user can make per minute.
This creates two risks:
1. **API cost explosion**: A buggy script or abusive user can send thousands of Gemini API
   requests, running up a very large bill.
2. **Brute force amplification**: Without rate limiting on login attempts, an attacker can
   try thousands of passwords per hour against the login form.

---

## Files You Need to Create/Change

| File | Change |
|------|--------|
| *(new)* `audit_log.py` | New module for security event logging |
| *(new)* `rate_limiter.py` | New module for query and login rate limiting |
| `auth.py` | Add audit log calls on login success/failure |
| `app.py` | Add rate limit check before processing each query |

---

## Step 4.1 — Create audit_log.py

**File: `audit_log.py`** (new file — create from scratch)

```python
# audit_log.py
# ── Security Audit Logging ────────────────────────────────
# Records all security-relevant events to audit_log.json.
#
# This module is intentionally simple — it writes one JSON record
# per event, appending to a flat file. For production at scale,
# this should be replaced with a proper SIEM or logging service,
# but for a small team this file-based approach is sufficient.
#
# audit_log.json is listed in .gitignore (not committed to Git).
# On Azure, it should be on a persistent volume (not inside the container).

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = 'audit_log.json'

# Event type constants — use these instead of raw strings to avoid typos
LOGIN_SUCCESS    = 'LOGIN_SUCCESS'
LOGIN_FAILED     = 'LOGIN_FAILED'
LOGOUT           = 'LOGOUT'
SESSION_EXPIRED  = 'SESSION_EXPIRED'
USER_CREATED     = 'USER_CREATED'
USER_DELETED     = 'USER_DELETED'
QUERY_EXECUTED   = 'QUERY_EXECUTED'
RATE_LIMIT_HIT   = 'RATE_LIMIT_HIT'


def log_security_event(
    event_type: str,
    username: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
    success: bool = True,
):
    """
    Append one security event record to audit_log.json.

    The audit log is append-only within each run. On each call, we:
    1. Read the existing file (if it exists)
    2. Append the new record
    3. Write to a temp file first, then atomic rename — this prevents
       a partial write from corrupting the entire log file.

    Why atomic write? If the server crashes mid-write, a direct write
    would leave a half-written JSON file that crashes json.load().
    The temp-file-then-rename approach is atomic on most filesystems:
    either the full new file exists, or the old one — never a partial.

    Args:
        event_type: One of the constants above (LOGIN_SUCCESS, etc.)
        username:   The user involved in the event
        details:    Dict with extra context (e.g. {'method': 'password'})
        ip_address: Source IP if available (Streamlit doesn't expose this easily)
        success:    Whether the action succeeded (True for most events)
    """
    try:
        record = {
            'timestamp':  datetime.now().isoformat(),
            'event_type': event_type,
            'username':   username,
            'ip_address': ip_address,
            'success':    success,
            'details':    details,
        }

        # Load existing log (or start fresh)
        log_path = Path(AUDIT_LOG_FILE)
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                if 'events' not in log_data:
                    log_data = {'events': []}
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt audit log detected — starting fresh")
                log_data = {'events': []}
        else:
            log_data = {'events': []}

        # Append new record
        log_data['events'].append(record)

        # Atomic write: write to .tmp first, then rename
        temp_path = Path(f'{AUDIT_LOG_FILE}.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        # os.rename is atomic on POSIX filesystems (Linux, macOS)
        temp_path.replace(log_path)

        # Also emit to the Python logger (shows in journalctl / Docker logs)
        logger.info(
            f"AUDIT | {event_type} | user={username} | "
            f"ip={ip_address or 'unknown'} | success={success}"
        )

    except Exception as e:
        # NEVER let audit logging break the main application.
        # Log the failure but do not re-raise.
        logger.error(f"Failed to write audit log: {e}")


def get_failed_logins_last_n_minutes(minutes: int = 60) -> list:
    """
    Return a list of LOGIN_FAILED events from the last N minutes.

    Use this in an admin dashboard or monitoring script to detect
    brute-force attempts. If you see many failed logins for the same
    username in a short period, that user's account is under attack.

    Args:
        minutes: Time window to look back (default 60)

    Returns:
        list of event dicts for LOGIN_FAILED events in the window
    """
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []

        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        cutoff_ts = datetime.now().timestamp() - (minutes * 60)

        return [
            event for event in log_data.get('events', [])
            if event.get('event_type') == LOGIN_FAILED
            and datetime.fromisoformat(event['timestamp']).timestamp() > cutoff_ts
        ]

    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []


def get_user_audit_trail(username: str, limit: int = 50) -> list:
    """
    Return the most recent audit events for a specific user.

    Useful in the admin panel to show an admin what actions a user
    has taken (logins, logouts, queries).

    Args:
        username: User to get trail for
        limit:    Maximum events to return (most recent first)

    Returns:
        list of event dicts, sorted newest first
    """
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []

        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        user_events = [
            e for e in log_data.get('events', [])
            if e.get('username') == username
        ]

        return sorted(user_events, key=lambda x: x['timestamp'], reverse=True)[:limit]

    except Exception as e:
        logger.error(f"Error reading audit trail for {username}: {e}")
        return []
```

---

## Step 4.2 — Create rate_limiter.py

**File: `rate_limiter.py`** (new file — create from scratch)

```python
# rate_limiter.py
# ── Rate Limiting ─────────────────────────────────────────
# Prevents API cost explosions and brute-force login attacks.
#
# Implementation: in-memory sliding window.
# All timestamps are stored in a defaultdict(list) in process memory.
# This means rate limit counters RESET when the server restarts.
# For a small SRE tool, this is acceptable — it's not a public API.
#
# How sliding window works:
#   For each username, we keep a list of timestamps of recent actions.
#   On each new action:
#   1. Remove timestamps older than the window (1 min or 1 hour)
#   2. Count remaining timestamps
#   3. If count >= limit → reject and return error message
#   4. If count < limit → allow and append current timestamp

from datetime import datetime, timedelta
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Limits ────────────────────────────────────────────────
MAX_QUERIES_PER_MINUTE = 10   # Per-user query rate (Gemini API calls)
MAX_QUERIES_PER_HOUR   = 100  # Per-user hourly cap

MAX_LOGIN_ATTEMPTS_PER_HOUR = 5  # Failed logins before lockout

# ── In-memory stores ──────────────────────────────────────
# defaultdict(list) creates an empty list for any new key automatically.
# Keys are usernames (strings), values are lists of datetime timestamps.
_query_timestamps: dict = defaultdict(list)
_failed_login_timestamps: dict = defaultdict(list)


def check_query_rate_limit(username: str) -> tuple:
    """
    Check whether a user is within their query rate limits.

    Called in app.py BEFORE sending a query to Gemini.
    If this returns (False, message), the query is blocked and the message
    is shown to the user instead of calling the Gemini API.

    Two limits are enforced independently:
    - Per-minute: prevents bursts from a fast script or copy-paste loop
    - Per-hour: prevents sustained high usage

    Args:
        username: The authenticated user making the query

    Returns:
        (True, "")           → query allowed, proceed
        (False, message)     → query blocked, show message to user
    """
    now = datetime.now()

    # Slide the window: remove timestamps older than 1 hour
    # (1 hour is the longest window we check, so anything older is irrelevant)
    _query_timestamps[username] = [
        ts for ts in _query_timestamps[username]
        if now - ts < timedelta(hours=1)
    ]

    # Count queries in the last minute
    recent_minute = [
        ts for ts in _query_timestamps[username]
        if now - ts < timedelta(minutes=1)
    ]

    if len(recent_minute) >= MAX_QUERIES_PER_MINUTE:
        logger.warning(f"Rate limit (1min) exceeded for user: {username}")
        return False, (
            f'⏱️ Query rate limit: you have sent {MAX_QUERIES_PER_MINUTE} queries '
            f'in the last minute. Please wait 60 seconds before asking another question.'
        )

    # Count queries in the last hour
    if len(_query_timestamps[username]) >= MAX_QUERIES_PER_HOUR:
        logger.warning(f"Rate limit (1hr) exceeded for user: {username}")
        return False, (
            f'⏱️ Hourly query limit reached ({MAX_QUERIES_PER_HOUR} queries/hour). '
            f'Please try again later or contact your SRE lead if you need higher limits.'
        )

    # Within limits — record this query timestamp
    _query_timestamps[username].append(now)
    return True, ''


def check_login_rate_limit(username: str) -> tuple:
    """
    Check whether a user has exceeded the failed login attempt limit.

    Called in auth.py's check_login() BEFORE attempting to verify the password.
    This prevents brute-force attacks by limiting how many times an attacker can
    try different passwords.

    IMPORTANT: This checks the FAILED ATTEMPT count (not total attempts).
    Successful logins call reset_login_attempts() to clear the counter.

    Args:
        username: Username being attempted (may not exist in users.json)

    Returns:
        (True, "")       → login attempt allowed, proceed with password check
        (False, message) → too many failures, block this attempt
    """
    now = datetime.now()

    # Clean up timestamps older than 1 hour
    _failed_login_timestamps[username] = [
        ts for ts in _failed_login_timestamps[username]
        if now - ts < timedelta(hours=1)
    ]

    if len(_failed_login_timestamps[username]) >= MAX_LOGIN_ATTEMPTS_PER_HOUR:
        logger.warning(f"Login rate limit exceeded for username: {username}")
        return False, (
            f'🔒 Too many failed login attempts for this account. '
            f'Please wait 1 hour before trying again, '
            f'or contact an administrator to reset your account.'
        )

    return True, ''


def record_failed_login(username: str):
    """
    Record a failed login attempt timestamp.

    Call this in auth.py when check_login() returns None (bad password
    or non-existent user). The timestamp is used by check_login_rate_limit()
    to determine if the user is locked out.

    Args:
        username: The username that failed (may not exist)
    """
    _failed_login_timestamps[username].append(datetime.now())
    logger.info(
        f"Failed login recorded for '{username}'. "
        f"Total in last hour: {len(_failed_login_timestamps[username])}"
    )


def reset_login_attempts(username: str):
    """
    Clear the failed login counter after a successful login.

    Call this in auth.py when check_login() returns a valid user_info dict.
    Without this, a user who forgets their password and gets locked out
    after 5 tries cannot log in again even after 1 hour (because we never
    cleaned their counter on success).

    Args:
        username: The username that just logged in successfully
    """
    _failed_login_timestamps[username] = []
    logger.info(f"Login attempt counter reset for '{username}' after successful login")


def get_rate_limit_status(username: str) -> dict:
    """
    Return current rate limit counters for a user (for admin/debug display).

    Args:
        username: User to check

    Returns:
        dict with query and login attempt counts and remaining allowances
    """
    now = datetime.now()

    recent_minute = sum(
        1 for ts in _query_timestamps[username]
        if now - ts < timedelta(minutes=1)
    )
    recent_hour = len(_query_timestamps[username])
    failed_logins = len(_failed_login_timestamps[username])

    return {
        'queries_last_minute':  recent_minute,
        'queries_last_hour':    recent_hour,
        'minute_limit':         MAX_QUERIES_PER_MINUTE,
        'hour_limit':           MAX_QUERIES_PER_HOUR,
        'minute_remaining':     max(0, MAX_QUERIES_PER_MINUTE - recent_minute),
        'hour_remaining':       max(0, MAX_QUERIES_PER_HOUR - recent_hour),
        'failed_logins_1hr':    failed_logins,
        'login_lockout_limit':  MAX_LOGIN_ATTEMPTS_PER_HOUR,
    }
```

---

## Step 4.3 — Update auth.py to Add Audit + Rate Limiting

You need to add **5 lines** to `auth.py`'s `check_login()` function.

Find the `check_login()` function in your already-updated `auth.py` (from Step 1).

**Replace the entire `check_login()` function** with this version that adds audit logging
and rate limiting:

```python
def check_login(username: str, password: str) -> Optional[Dict]:
    """
    Verify username and password. Returns user info dict on success, None on failure.

    This version adds:
    - Rate limiting: blocks login after 5 failed attempts per hour
    - Audit logging: records every success and failure to audit_log.json
    """
    # Import here to avoid circular imports at module load time.
    # Both modules are only needed when check_login() is actually called,
    # not at import time.
    from audit_log import log_security_event, LOGIN_SUCCESS, LOGIN_FAILED
    from rate_limiter import check_login_rate_limit, record_failed_login, reset_login_attempts

    try:
        if not username or not password:
            logger.warning("Login attempt with empty username or password")
            return None

        # ── Rate limit check (BEFORE loading users or checking password) ──
        # This must come first to prevent attackers from bypassing the limit
        # by providing different usernames (we track per-username).
        rate_ok, rate_message = check_login_rate_limit(username)
        if not rate_ok:
            # Log the blocked attempt to the audit trail
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'rate_limited', 'message': rate_message},
                success=False
            )
            # Return a generic error — don't expose the rate limit message
            # to the UI directly (to avoid giving attackers information).
            # app.py will show 'Incorrect username or password.' regardless.
            logger.warning(f"Login blocked by rate limiter for: {username}")
            return None

        try:
            users = load_users()
        except FileNotFoundError:
            logger.error("Users file not found during login")
            raise
        except Exception as e:
            logger.error(f"Failed to load users during login: {e}")
            return None

        if username not in users:
            logger.info(f"Login attempt for non-existent user: {username}")
            # Record failure and log to audit trail
            record_failed_login(username)
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'user_not_found'},
                success=False
            )
            # Still run a dummy verify to maintain constant response time
            verify_password(password, "$2b$12$dummyhashfornon.existentuserXXXXXXXXXXXXXXXXXXXXXXXX")
            return None

        user = users[username]

        if not isinstance(user, dict) or 'password_hash' not in user:
            logger.error(f"Invalid user data structure for {username}")
            return None

        stored_hash = user['password_hash']

        if not verify_password(password, stored_hash):
            logger.info(f"Failed login attempt for user: {username}")
            # Record failure for rate limiting AND audit trail
            record_failed_login(username)
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'wrong_password'},
                success=False
            )
            return None

        # ── Successful login ───────────────────────────────
        logger.info(f"Successful login for user: {username}")
        # Clear the failed login counter so they don't get locked out
        # in future sessions after previously failing attempts.
        reset_login_attempts(username)
        # Record success in audit trail
        log_security_event(
            LOGIN_SUCCESS, username,
            {'role': user.get('role', 'sre'), 'method': 'password'},
            success=True
        )

        return {
            'username':     username,
            'display_name': user.get('display_name', username),
            'customers':    user.get('customers', ['ALL']),
            'role':         user.get('role', 'sre')
        }

    except Exception as e:
        logger.error(f"Unexpected error in check_login: {e}")
        return None
```

---

## Step 4.4 — Update app.py to Add Query Rate Limiting

Add a rate limit check to `app.py` right before the query is processed.

Find this block in `app.py` (the `if prompt:` section, around line 207):

```python
# CURRENT CODE:
if prompt:
    # REMOVED: Customer scope check

    # 1. Display the user's question
    with st.chat_message('user'):
        st.write(prompt)
```

Replace with:

```python
# UPDATED CODE — add rate limit check before any Gemini API call:
if prompt:
    # ── Rate limit check ───────────────────────────────────
    # Check BEFORE displaying the user's question or calling Gemini.
    # If blocked, show an error and stop — no API call is made.
    from rate_limiter import check_query_rate_limit

    query_allowed, rate_message = check_query_rate_limit(current_user)

    if not query_allowed:
        st.error(rate_message)
        st.info('💡 Rate limits ensure fair API usage across the team.')
        st.stop()
    # ──────────────────────────────────────────────────────

    # 1. Display the user's question
    with st.chat_message('user'):
        st.write(prompt)
```

**Why stop before displaying the question?**
If we blocked after showing the question in the chat, the user's message would appear
in the chat history but get no answer — confusing. Blocking before the display keeps
the UI state consistent.

---

## Step 4.5 — Test Audit Logging

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

python3 - << 'EOF'
import os
# Clean up any existing test log
if os.path.exists('audit_log.json'):
    os.rename('audit_log.json', 'audit_log.json.pre_test_backup')

from audit_log import log_security_event, get_failed_logins_last_n_minutes
from audit_log import LOGIN_SUCCESS, LOGIN_FAILED

# Test 1: Log a success event
log_security_event(LOGIN_SUCCESS, 'alice', {'method': 'password', 'role': 'senior_sre'})
print("PASS: Logged LOGIN_SUCCESS event")

# Test 2: Log a failure event
log_security_event(LOGIN_FAILED, 'attacker', {'reason': 'wrong_password'}, success=False)
print("PASS: Logged LOGIN_FAILED event")

# Test 3: Query failed logins
failed = get_failed_logins_last_n_minutes(60)
assert len(failed) == 1, f"Expected 1 failed login, got {len(failed)}"
assert failed[0]['username'] == 'attacker', "Wrong username in failed login"
print("PASS: get_failed_logins_last_n_minutes() works correctly")

# Test 4: Verify audit_log.json was created
import json
with open('audit_log.json') as f:
    data = json.load(f)
assert len(data['events']) == 2, f"Expected 2 events, got {len(data['events'])}"
print("PASS: audit_log.json has correct structure")

print()
print("All audit log tests passed.")
EOF
```

## Step 4.6 — Test Rate Limiting

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

python3 - << 'EOF'
from rate_limiter import (
    check_query_rate_limit, check_login_rate_limit,
    record_failed_login, reset_login_attempts
)

# Test 1: First 10 queries should be allowed
for i in range(10):
    allowed, msg = check_query_rate_limit('testuser')
    assert allowed, f"Query {i+1} should be allowed but was blocked: {msg}"
print("PASS: First 10 queries per minute allowed")

# Test 2: 11th query should be blocked
allowed, msg = check_query_rate_limit('testuser')
assert not allowed, "11th query should be blocked"
assert 'rate limit' in msg.lower(), f"Wrong error message: {msg}"
print("PASS: 11th query blocked with correct message")

# Test 3: Login rate limiting
for i in range(5):
    record_failed_login('victim_user')

blocked, msg = check_login_rate_limit('victim_user')
assert not blocked, "Should be blocked after 5 failed logins"
print("PASS: Account locked after 5 failed logins")

# Test 4: Reset clears the counter
reset_login_attempts('victim_user')
allowed, msg = check_login_rate_limit('victim_user')
assert allowed, "Should be allowed after reset"
print("PASS: Login counter resets correctly after successful login")

print()
print("All rate limiter tests passed.")
EOF
```

---

## How This Fits the Application Security Model

```
Attack Scenario: Brute Force Login Attempt
──────────────────────────────────────────

Attacker tries password #1, #2, #3, #4, #5:
  → Each attempt: check_login_rate_limit() allows (count < 5)
  → Each attempt: verify_password() takes ~100ms (bcrypt)
  → Each attempt: record_failed_login() increments counter
  → Each attempt: log_security_event(LOGIN_FAILED) writes to audit_log.json
  → After 5 attempts: check_login_rate_limit() returns False → blocked for 1 hour
  → Total time for 5 attempts: ~500ms (bcrypt) + overhead
  → Admin can see 5 LOGIN_FAILED events in audit_log.json for same username

Without bcrypt + rate limiting: attacker can try 1 BILLION/sec
With bcrypt + rate limiting: attacker is limited to 5 attempts/hour
```

```
Normal User Scenario: Heavy Query Day
──────────────────────────────────────

SRE uses the tool heavily, sends 10 queries in 1 minute:
  → Queries 1-10: check_query_rate_limit() allows each
  → Query 11: rate limit hit → "Please wait 60 seconds"
  → 60 seconds later: timestamp window slides, all 10 old ones expire
  → Query 12 (now): allowed again (0 in last minute)
  → After 100 queries total in the hour: hourly cap hit
  → "Hourly query limit reached"
```
