# auth.py
# ── Enterprise Authentication with bcrypt ─────────────────
# Replaces the previous SHA-256 hashing with bcrypt.
# bcrypt is intentionally slow (~100ms per hash) which makes
# brute-force attacks computationally infeasible.

import bcrypt
import logging
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




def load_users() -> dict:
    """
    Load all users from the PostgreSQL database.
    Returns the same dict format as before: {username: {password_hash, display_name, customers, role}}
    so the rest of the code (check_login, admin panel) needs no changes.
    """
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT username, password_hash, display_name, customers, role FROM users"
                )
                rows = cur.fetchall()

        return {
            row[0]: {
                'password_hash': row[1],
                'display_name':  row[2] or row[0],
                'customers':     list(row[3]) if row[3] else ['ALL'],
                'role':          row[4] or 'sre',
            }
            for row in rows
        }

    except Exception as e:
        logger.error(f'Error loading users from database: {e}')
        raise

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with automatic salt generation.

    How it works:
    1. bcrypt.gensalt(rounds=12) generates a random 22-character salt.
       The 'rounds=12' means bcrypt will perform 2^12 = 4096 iterations
       of its internal Blowfish cipher. This takes ~100ms on modern hardware.
    2. bcrypt.hashpw() combines the password + salt through those 4096
       iterations and returns a 60-character string like:
       $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7LQv3c1yqB
       │  │  │                    │
       │  │  └── salt (22 chars) └── hash (31 chars)
       │  └── cost factor (12)
       └── bcrypt version identifier

    The salt is embedded IN the output hash, so you don't store it
    separately — bcrypt.checkpw() extracts it automatically later.

    Args:
        password: Plain-text password string

    Returns:
        str: A 60-character bcrypt hash string (includes salt)
    """
    try:
        if not password:
            raise ValueError("Password cannot be empty")

        # rounds=12 is the industry standard balance of security vs speed.
        # rounds=10 is minimum acceptable; rounds=14+ is very slow but
        # provides additional protection as hardware improves.
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

        # bcrypt returns bytes; decode to str for JSON storage
        return hashed.decode('utf-8')

    except Exception as e:
        logger.error(f'Password hashing error: {e}')
        raise


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    How it works:
    1. bcrypt.checkpw() extracts the salt from stored_hash (first 29 chars).
    2. It hashes the provided password using the SAME salt and cost factor.
    3. It compares the two hashes using constant-time comparison to prevent
       timing attacks (an attacker cannot measure response time to guess
       how many characters of the hash matched).

    This is fundamentally different from SHA-256 where you would do:
        hashlib.sha256(password).hexdigest() == stored_hash
    That comparison is NOT constant-time and is also fast to brute force.

    Args:
        password: Plain-text password to check
        stored_hash: The bcrypt hash string from users.json

    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        if not password or not stored_hash:
            return False

        # bcrypt.checkpw handles salt extraction, hashing, and constant-time
        # comparison all in one call.
        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )

    except Exception as e:
        logger.error(f'Password verification error: {e}')
        return False

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

        
def get_user_customers(username: str) -> list:
    """Get the list of customers a user can access."""
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT customers FROM users WHERE username = %s",
                    (username,)
                )
                row = cur.fetchone()

        if row is None:
            logger.warning(f"User {username} not found when getting customers")
            return ['ALL']

        customers = row[0]
        return list(customers) if customers else ['ALL']

    except Exception as e:
        logger.error(f"Error getting customers for {username}: {e}")
        return ['ALL']

def create_user(username: str, password: str, display_name: str, role: str = 'sre') -> bool:
    """
    Insert a new user into the PostgreSQL users table.
    Returns True if created, False if username already exists.
    """
    from db import get_db
    try:
        password_hash = hash_password(password)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, customers, role)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING username
                    """,
                    (username, password_hash, display_name, ['ALL'], role)
                )
                result = cur.fetchone()

        # ON CONFLICT DO NOTHING means: if username already exists, skip silently.
        # RETURNING username means: if a row WAS inserted, return it.
        # If result is None, the username already existed (nothing was inserted).
        if result is None:
            logger.warning(f"Attempted to create existing user: {username}")
            return False

        logger.info(f"User created: {username}")
        return True

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def delete_user(username: str) -> bool:
    """
    Delete a user from the PostgreSQL users table.
    Returns True if deleted, False if user did not exist.
    """
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM users WHERE username = %s RETURNING username",
                    (username,)
                )
                result = cur.fetchone()

        # RETURNING username gives us back the deleted row.
        # If result is None, the user did not exist.
        if result is None:
            logger.warning(f"Attempted to delete non-existent user: {username}")
            return False

        logger.info(f"User deleted: {username}")
        return True

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False