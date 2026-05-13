# auth/auth.py
# ── Enterprise Authentication with bcrypt ─────────────────

import bcrypt
import json
import logging
from pathlib import Path
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = 'users.json'


def load_users() -> dict:
    """Load user data from users.json."""
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
        except FileNotFoundError:
            logger.error("Users file not found during login")
            raise
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

        stored_hash = user['password_hash']

        if not verify_password(password, stored_hash):
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
    """Create a new user and save to users.json."""
    try:
        users = load_users()

        if username in users:
            logger.warning(f"Attempted to create existing user: {username}")
            return False

        password_hash = hash_password(password)

        users[username] = {
            'password_hash': password_hash,
            'display_name': display_name,
            'customers': ['ALL'],
            'role': role
        }

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
    """Delete a user from users.json."""
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
