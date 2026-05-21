# auth/auth.py
# ── Enterprise Authentication with bcrypt + PostgreSQL ────

import bcrypt
import logging
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_users() -> dict:
    """
    Load all users from the PostgreSQL database.
    Returns {username: {password_hash, display_name, customers, role}}.
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
    """Hash a password using bcrypt with automatic salt generation."""
    try:
        if not password:
            raise ValueError("Password cannot be empty")

        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    except Exception as e:
        logger.error(f'Password hashing error: {e}')
        raise


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        if not password or not stored_hash:
            return False

        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )

    except Exception as e:
        logger.error(f'Password verification error: {e}')
        return False


def check_login(username: str, password: str) -> Optional[Dict]:
    """Verify username and password. Returns user info dict on success, None on failure."""
    from monitoring.audit_log import log_security_event, LOGIN_SUCCESS, LOGIN_FAILED
    from auth.rate_limiter import check_login_rate_limit, record_failed_login, reset_login_attempts

    try:
        if not username or not password:
            logger.warning("Login attempt with empty username or password")
            return None

        rate_ok, rate_message = check_login_rate_limit(username)
        if not rate_ok:
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'rate_limited', 'message': rate_message},
                success=False
            )
            logger.warning(f"Login blocked by rate limiter for: {username}")
            return None

        try:
            users = load_users()
        except Exception as e:
            logger.error(f"Failed to load users during login: {e}")
            return None

        if username not in users:
            logger.info(f"Login attempt for non-existent user: {username}")
            record_failed_login(username)
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'user_not_found'},
                success=False
            )
            verify_password(password, "$2b$12$dummyhashfornon.existentuserXXXXXXXXXXXXXXXXXXXXXXXX")
            return None

        user = users[username]

        if not isinstance(user, dict) or 'password_hash' not in user:
            logger.error(f"Invalid user data structure for {username}")
            return None

        if not verify_password(password, user['password_hash']):
            logger.info(f"Failed login attempt for user: {username}")
            record_failed_login(username)
            log_security_event(
                LOGIN_FAILED, username,
                {'reason': 'wrong_password'},
                success=False
            )
            return None

        logger.info(f"Successful login for user: {username}")
        reset_login_attempts(username)
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


def get_user_info(username: str) -> Optional[Dict]:
    """
    Look up a user by username without checking a password.

    Used by the cookie-based session restore: the signed cookie already
    proves identity, so we just need fresh role/customer data from the DB.
    Returns the same dict shape as check_login() on success, None if missing.
    """
    try:
        users = load_users()
        user = users.get(username)
        if not user:
            return None
        return {
            'username':     username,
            'display_name': user.get('display_name', username),
            'customers':    user.get('customers', ['ALL']),
            'role':         user.get('role', 'sre'),
        }
    except Exception as e:
        logger.error(f'Error loading user info for {username}: {e}')
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

        return list(row[0]) if row[0] else ['ALL']

    except Exception as e:
        logger.error(f"Error getting customers for {username}: {e}")
        return ['ALL']


def create_user(username: str, password: str, display_name: str, role: str = 'sre') -> bool:
    """Insert a new user into the PostgreSQL users table."""
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

        if result is None:
            logger.warning(f"Attempted to create existing user: {username}")
            return False

        logger.info(f"User created: {username}")
        return True

    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False


def delete_user(username: str) -> bool:
    """Delete a user from the PostgreSQL users table."""
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM users WHERE username = %s RETURNING username",
                    (username,)
                )
                result = cur.fetchone()

        if result is None:
            logger.warning(f"Attempted to delete non-existent user: {username}")
            return False

        logger.info(f"User deleted: {username}")
        return True

    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False
