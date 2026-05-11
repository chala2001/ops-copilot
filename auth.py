# auth.py
# ── Authentication module ───────────────────────────────
# Handles login, session validation, and user permissions.

import hashlib
import json
import os
from pathlib import Path

USERS_FILE = 'users.json'

def load_users() -> dict:
    '''Load user data from users.json.'''
    if not Path(USERS_FILE).exists():
        raise FileNotFoundError(
            f'{USERS_FILE} not found. Create it with user credentials.'
        )
    with open(USERS_FILE) as f:
        return json.load(f)['users']

def hash_password(password: str) -> str:
    '''Hash a password using SHA-256.'''
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(username: str, password: str) -> dict | None:
    '''
    Verify username and password.
    Returns user info dict if correct, None if wrong.
    '''
    users = load_users()

    if username not in users:
        return None

    user = users[username]
    provided_hash = hash_password(password)

    if provided_hash != user['password_hash']:
        return None

    # Correct! Return user info (without the password hash)
    return {
        'username':     username,
        'display_name': user['display_name'],
        'customers':    user['customers'],
        'role':         user['role']
    }

def get_user_customers(username: str) -> list:
    '''Get the list of customers a user can access.'''
    users = load_users()
    return users.get(username, {}).get('customers', ['General'])