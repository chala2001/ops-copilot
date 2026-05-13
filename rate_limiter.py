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