# auth.py - Authentication with Complete Exception Handling

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = 'users.json'

def load_users() -> dict:
    '''Load user data from users.json with error handling.'''
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
    '''Hash a password using SHA-256 with error handling.'''
    try:
        if not password:
            raise ValueError("Password cannot be empty")
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.error(f'Password hashing error: {e}')
        raise

def check_login(username: str, password: str) -> Optional[Dict]:
    '''
    Verify username and password with complete error handling.
    Returns user info dict if correct, None if wrong.
    '''
    try:
        # Input validation
        if not username or not password:
            logger.warning("Empty username or password")
            return None
        
        # Load users
        try:
            users = load_users()
        except FileNotFoundError:
            logger.error("Users file not found during login")
            raise
        except Exception as e:
            logger.error(f"Failed to load users during login: {e}")
            return None

        # Check if user exists
        if username not in users:
            logger.info(f"Login attempt for non-existent user: {username}")
            return None

        user = users[username]
        
        # Validate user data structure
        if not isinstance(user, dict):
            logger.error(f"Invalid user data structure for {username}")
            return None
        
        if 'password_hash' not in user:
            logger.error(f"Missing password_hash for user {username}")
            return None
        
        # Hash provided password
        try:
            provided_hash = hash_password(password)
        except Exception as e:
            logger.error(f"Failed to hash password during login: {e}")
            return None

        # Compare hashes
        if provided_hash != user['password_hash']:
            logger.info(f"Failed login attempt for user: {username}")
            return None

        # Successful login - return user info
        logger.info(f"Successful login for user: {username}")
        
        return {
            'username':     username,
            'display_name': user.get('display_name', username),
            'customers':    user.get('customers', ['General']),
            'role':         user.get('role', 'user')
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in check_login: {e}")
        return None

def get_user_customers(username: str) -> list:
    '''Get the list of customers a user can access with error handling.'''
    try:
        users = load_users()
        
        if username not in users:
            logger.warning(f"User {username} not found when getting customers")
            return ['General']
        
        customers = users[username].get('customers', ['General'])
        
        # Validate customers is a list
        if not isinstance(customers, list):
            logger.warning(f"Invalid customers format for {username}")
            return ['General']
        
        return customers
    
    except Exception as e:
        logger.error(f"Error getting customers for {username}: {e}")
        return ['General']