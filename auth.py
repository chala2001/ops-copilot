# auth.py
# ── Enterprise Authentication with bcrypt ─────────────────
# Replaces the previous SHA-256 hashing with bcrypt.
# bcrypt is intentionally slow (~100ms per hash) which makes
# brute-force attacks computationally infeasible.

import bcrypt
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = 'users.json'


def load_users() -> dict:
    """
    Load user data from users.json.

    Returns the inner 'users' dict on success.
    Raises FileNotFoundError or ValueError on bad file state.

    This function is called on EVERY login attempt so it always
    reads the latest users.json from disk — no caching. This means
    you can add/remove users without restarting the app.
    """
    try:
        if not Path(USERS_FILE).exists():
            logger.error(f'{USERS_FILE} not found')
            raise FileNotFoundError(
                f'{USERS_FILE} not found. Create it with user credentials.'
            )

        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if 'users' not in data:
            logger.error(f'{USERS_FILE} missing "users" key')
            raise ValueError(f'{USERS_FILE} has invalid format')

        return data['users']

    except json.JSONDecodeError as e:
        logger.error(f'Invalid JSON in {USERS_FILE}: {e}')
        raise ValueError(f'{USERS_FILE} contains invalid JSON')
    except Exception as e:
        logger.error(f'Error loading users: {e}')
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
    try:
        users = load_users()

        if username not in users:
            logger.warning(f"User {username} not found when getting customers")
            return ['ALL']

        customers = users[username].get('customers', ['ALL'])

        if not isinstance(customers, list):
            logger.warning(f"Invalid customers format for {username}")
            return ['ALL']

        return customers

    except Exception as e:
        logger.error(f"Error getting customers for {username}: {e}")
        return ['ALL']


def create_user(username: str, password: str, display_name: str, role: str = 'sre') -> bool:
    """
    Create a new user and save to users.json.

    This is called by the Admin Panel (pages/5_Admin_Panel.py).
    The password is hashed with bcrypt before saving — the plain-text
    password is NEVER stored anywhere.

    Args:
        username: Unique login name (no spaces)
        password: Plain-text password (will be bcrypt-hashed immediately)
        display_name: Full name shown in the UI
        role: One of 'sre', 'senior_sre', 'admin'

    Returns:
        True if created, False if username already exists
    """
    try:
        users = load_users()

        if username in users:
            logger.warning(f"Attempted to create existing user: {username}")
            return False

        # Hash with bcrypt BEFORE storing
        password_hash = hash_password(password)

        users[username] = {
            'password_hash': password_hash,
            'display_name': display_name,
            'customers': ['ALL'],
            'role': role
        }

        # Read full file, update users section, write back
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['users'] = users

        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"User created: {username}")
        return True

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False


def delete_user(username: str) -> bool:
    """
    Delete a user from users.json.

    Args:
        username: Username to delete

    Returns:
        True if deleted, False if user doesn't exist or error
    """
    try:
        users = load_users()

        if username not in users:
            logger.warning(f"Attempted to delete non-existent user: {username}")
            return False

        del users[username]

        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data['users'] = users

        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"User deleted: {username}")
        return True

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False