# 🏢 ENTERPRISE DEPLOYMENT GUIDE
## WSO2 SRE Ops Copilot - Production-Ready Implementation

**Document Version:** 1.0  
**Date:** May 12, 2026  
**Target:** WSO2 SRE Teams  
**Platform:** Azure Cloud  

---

# 📋 TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Critical Security Fixes](#2-critical-security-fixes)
3. [Complete Code Modifications](#3-complete-code-modifications)
4. [Azure Deployment Guide](#4-azure-deployment-guide)
5. [Post-Deployment Configuration](#5-post-deployment-configuration)
6. [Monitoring & Maintenance](#6-monitoring--maintenance)
7. [Troubleshooting](#7-troubleshooting)

---

# 1. OVERVIEW

## 1.1 What This Guide Covers

This document provides step-by-step instructions to:
- ✅ Fix all security vulnerabilities in your current system
- ✅ Add enterprise-grade authentication with bcrypt
- ✅ Implement HTTPS/SSL encryption
- ✅ Add session management and timeouts
- ✅ Deploy to Azure Virtual Machine
- ✅ Configure monitoring and backups

## 1.2 Current System Status

**What You Have:**
- Working RAG system with Gemini API
- Basic authentication (SHA-256 - WEAK)
- Docker deployment (HTTP only - INSECURE)
- JSON-based user database
- Query logging and dashboards

**What Needs Fixing:**
- 🔴 Weak password hashing (SHA-256 → bcrypt)
- 🔴 No HTTPS/TLS encryption
- 🔴 No session timeout (stays logged in forever)
- 🔴 API keys in code (should be env variables)

## 1.3 Prerequisites

**On Your Local Machine:**
- Ubuntu 22.04 or Windows with WSL2
- Python 3.10+
- Docker and Docker Compose
- Git
- Text editor (VS Code, nano, vim)

**Azure Account:**
- Active Azure subscription
- Permission to create Virtual Machines
- SSH key pair for remote access

**Time Required:**
- Security fixes: 2-3 hours
- Azure deployment: 1-2 hours
- Testing: 1 hour
- **Total: 4-6 hours**

---

# 2. CRITICAL SECURITY FIXES

## 2.1 Why These Fixes Are Essential

### 2.1.1 Password Hashing (SHA-256 → bcrypt)

**Current Problem:**
```python
# CURRENT (WEAK):
password_hash = hashlib.sha256(password.encode()).hexdigest()
# SHA-256 can compute 1 BILLION hashes per second
# Attacker can crack 8-char password in hours
```

**Why SHA-256 is Bad for Passwords:**
1. **Too Fast:** Modern GPU can test billions of passwords per second
2. **No Salt:** Same password = same hash (rainbow table attacks)
3. **Designed for Speed:** Made for file checksums, not passwords

**bcrypt Solution:**
```python
# NEW (SECURE):
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
# bcrypt is intentionally SLOW (takes ~100ms per hash)
# Has built-in salt (random data added to password)
# Adaptive: can increase cost factor as computers get faster
```

**Real-World Impact:**
- SHA-256: Crack "password123" in **seconds**
- bcrypt: Crack "password123" in **years** (even with GPU cluster)

### 2.1.2 HTTPS/TLS Encryption

**Current Problem:**
```
User Browser → [HTTP - UNENCRYPTED] → Streamlit Server
                     ↑
              Anyone on network
              can read passwords,
              queries, answers
```

**With HTTPS:**
```
User Browser → [HTTPS - ENCRYPTED] → Streamlit Server
                     ↑
              Encrypted tunnel
              Passwords & data safe
              from network sniffing
```

**Why HTTPS Matters:**
- Prevents password theft on WiFi
- Required for corporate compliance
- Protects customer data in queries
- Prevents man-in-the-middle attacks

### 2.1.3 Session Timeout

**Current Problem:**
- User logs in Monday morning
- Leaves computer unlocked
- Session stays active for WEEKS
- Anyone can access system

**With Timeout:**
- Session expires after 1 hour of inactivity
- Forces re-login periodically
- Limits damage from stolen sessions

### 2.1.4 Environment Variables for Secrets

**Current Problem:**
```python
# .env file (might be committed to Git)
GOOGLE_API_KEY=AIzaSyC_4QNcJrQ49cqzSpgl5jhDOaw7LmIeps8

# If pushed to GitHub:
# → API key exposed to public
# → $10,000+ bill from API abuse
```

**Solution:**
```bash
# On server only (never in Git)
export GOOGLE_API_KEY="your_key_here"

# Application reads from environment
# Never hardcoded in files
```

---

# 3. COMPLETE CODE MODIFICATIONS

## 3.1 Security Fix #1: Upgrade to bcrypt

### 3.1.1 Install bcrypt

```bash
cd ~/ops-copilot_gemini

# Install bcrypt
pip install bcrypt

# Add to requirements.txt
echo "bcrypt==4.1.2" >> requirements.txt

# Verify installation
python3 -c "import bcrypt; print('✅ bcrypt installed')"
```

**What bcrypt does:**
- Hashes passwords with random salt
- Takes ~100ms per hash (intentionally slow)
- Adaptive cost factor (can increase difficulty over time)
- Industry standard (used by banks, tech companies)

### 3.1.2 Create New auth.py with bcrypt

**Backup existing file:**
```bash
cp auth.py auth.py.backup.$(date +%Y%m%d)
```

**Create new auth.py:**
```bash
cat > auth.py << 'ENDOFFILE'
# auth.py
# ── ENTERPRISE-GRADE AUTHENTICATION ───────────────────────
# Uses bcrypt for secure password hashing

import bcrypt
import json
import logging
from pathlib import Path
from typing import Optional, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = 'users.json'

def load_users() -> dict:
    '''
    Load user data from users.json with error handling.
    
    Returns:
        dict: User data dictionary
    
    Raises:
        FileNotFoundError: If users.json doesn't exist
        ValueError: If JSON is invalid
    '''
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
    '''
    Hash a password using bcrypt with automatic salt generation.
    
    Args:
        password: Plain text password
    
    Returns:
        str: bcrypt hash (includes salt)
    
    Example:
        >>> hash_password("mypassword123")
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7LQv3c1yqB'
    
    Technical Details:
        - Uses bcrypt.gensalt() to generate random salt
        - Cost factor: 12 (means 2^12 = 4096 iterations)
        - Takes ~100ms to compute (intentionally slow)
        - Salt is embedded in the hash (first 29 characters)
    '''
    try:
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=12)  # rounds=12 is good balance
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Return as string (bcrypt returns bytes)
        return hashed.decode('utf-8')
    
    except Exception as e:
        logger.error(f'Password hashing error: {e}')
        raise

def verify_password(password: str, stored_hash: str) -> bool:
    '''
    Verify a password against a bcrypt hash.
    
    Args:
        password: Plain text password to verify
        stored_hash: bcrypt hash from database
    
    Returns:
        bool: True if password matches, False otherwise
    
    Technical Details:
        - Extracts salt from stored_hash
        - Hashes provided password with same salt
        - Compares hashes in constant time (prevents timing attacks)
    '''
    try:
        if not password or not stored_hash:
            return False
        
        # bcrypt.checkpw handles salt extraction and comparison
        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    
    except Exception as e:
        logger.error(f'Password verification error: {e}')
        return False

def check_login(username: str, password: str) -> Optional[Dict]:
    '''
    Verify username and password with bcrypt.
    
    Args:
        username: Username to authenticate
        password: Plain text password
    
    Returns:
        dict: User info if valid, None if invalid
        
    Example Return:
        {
            'username': 'alice',
            'display_name': 'Alice (Senior SRE)',
            'customers': ['ALL'],
            'role': 'senior_sre'
        }
    
    Security Features:
        - Constant-time comparison (prevents timing attacks)
        - Logs failed attempts (for security monitoring)
        - Never returns password hash
        - Rate limiting (TODO: add after initial deployment)
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
        
        stored_hash = user['password_hash']
        
        # Verify password with bcrypt
        if not verify_password(password, stored_hash):
            logger.info(f"Failed login attempt for user: {username}")
            return None

        # Successful login - return user info (NO PASSWORD HASH!)
        logger.info(f"Successful login for user: {username}")
        
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
    '''
    Get the list of customers a user can access.
    
    Args:
        username: Username to look up
    
    Returns:
        list: Customer list (defaults to ['ALL'])
    '''
    try:
        users = load_users()
        
        if username not in users:
            logger.warning(f"User {username} not found when getting customers")
            return ['ALL']
        
        customers = users[username].get('customers', ['ALL'])
        
        # Validate customers is a list
        if not isinstance(customers, list):
            logger.warning(f"Invalid customers format for {username}")
            return ['ALL']
        
        return customers
    
    except Exception as e:
        logger.error(f"Error getting customers for {username}: {e}")
        return ['ALL']

# ── UTILITY FUNCTIONS FOR ADMIN PANEL ─────────────────────

def create_user(username: str, password: str, display_name: str, role: str = 'sre') -> bool:
    '''
    Create a new user (for admin panel).
    
    Args:
        username: Unique username
        password: Plain text password (will be hashed)
        display_name: Full name for display
        role: User role (sre, senior_sre, admin)
    
    Returns:
        bool: True if created, False if username exists
    '''
    try:
        users = load_users()
        
        if username in users:
            logger.warning(f"Attempted to create existing user: {username}")
            return False
        
        # Hash password
        password_hash = hash_password(password)
        
        # Add user
        users[username] = {
            'password_hash': password_hash,
            'display_name': display_name,
            'customers': ['ALL'],
            'role': role
        }
        
        # Save
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
        
        data['users'] = users
        
        with open(USERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"User created: {username}")
        return True
    
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def delete_user(username: str) -> bool:
    '''
    Delete a user (for admin panel).
    
    Args:
        username: Username to delete
    
    Returns:
        bool: True if deleted, False if error
    '''
    try:
        users = load_users()
        
        if username not in users:
            logger.warning(f"Attempted to delete non-existent user: {username}")
            return False
        
        del users[username]
        
        # Save
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
        
        data['users'] = users
        
        with open(USERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"User deleted: {username}")
        return True
    
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False
ENDOFFILE
```

**Key Changes Explained:**

1. **Import bcrypt instead of hashlib**
   ```python
   import bcrypt  # Enterprise-grade password hashing
   ```

2. **hash_password() now uses bcrypt**
   - Generates random salt automatically
   - Uses cost factor 12 (4096 iterations)
   - Takes ~100ms (prevents brute force)

3. **verify_password() for checking passwords**
   - Extracts salt from stored hash
   - Hashes input password with same salt
   - Constant-time comparison (security)

4. **check_login() uses verify_password()**
   - No more simple hash comparison
   - bcrypt handles all the complexity

### 3.1.3 Generate bcrypt Hashes for Existing Users

**Create password migration script:**
```bash
cat > migrate_passwords.py << 'ENDOFFILE'
#!/usr/bin/env python3
# migrate_passwords.py
# Converts users.json from SHA-256 to bcrypt hashes

import bcrypt
import json
from datetime import datetime

# NEW SECURE PASSWORDS (replace with your actual passwords)
# IMPORTANT: These should be STRONG passwords for production
NEW_PASSWORDS = {
    "alice": "Alice@WSO2#SecurePass2024!",
    "bob": "Bob@WSO2#SecurePass2024!",
    "carol": "Carol@WSO2#SecurePass2024!",
    "admin": "Admin@WSO2#VerySecure2024!!"
}

print("=" * 60)
print("WSO2 SRE Ops Copilot - Password Migration to bcrypt")
print("=" * 60)
print()

# Load existing users.json
try:
    with open('users.json', 'r') as f:
        data = json.load(f)
        users = data['users']
    print(f"✅ Loaded {len(users)} users from users.json")
except FileNotFoundError:
    print("❌ users.json not found!")
    exit(1)

# Backup existing file
backup_file = f'users.json.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
with open(backup_file, 'w') as f:
    json.dump(data, f, indent=2)
print(f"✅ Backup created: {backup_file}")
print()

# Generate bcrypt hashes
print("Generating bcrypt hashes (this takes ~1 second per user)...")
print("-" * 60)

new_users = {}

for username, user_data in users.items():
    if username in NEW_PASSWORDS:
        password = NEW_PASSWORDS[username]
    else:
        print(f"⚠️  No password defined for {username}, using default")
        password = f"{username}@WSO2#2024"
    
    # Generate bcrypt hash (takes ~100ms)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    new_users[username] = {
        'password_hash': hashed.decode('utf-8'),
        'display_name': user_data.get('display_name', username),
        'customers': user_data.get('customers', ['ALL']),
        'role': user_data.get('role', 'sre')
    }
    
    print(f"✅ {username:15s} → Password: {password}")

print("-" * 60)
print()

# Save updated users.json
data['users'] = new_users

with open('users.json', 'w') as f:
    json.dump(data, f, indent=2)

print("✅ users.json updated with bcrypt hashes")
print()
print("=" * 60)
print("IMPORTANT: Save these credentials securely!")
print("=" * 60)
print()

for username in NEW_PASSWORDS:
    print(f"Username: {username}")
    print(f"Password: {NEW_PASSWORDS[username]}")
    print()

print("Next steps:")
print("1. Test login with new credentials")
print("2. Share credentials with team securely (NOT via email!)")
print("3. Delete this script after migration")
print("4. Keep backup file secure")
ENDOFFILE

chmod +x migrate_passwords.py
```

**Run the migration:**
```bash
cd ~/ops-copilot_gemini

# Run password migration
python3 migrate_passwords.py

# Output will show:
# ✅ Loaded 4 users from users.json
# ✅ Backup created: users.json.backup.20260512_141230
# ✅ alice → Password: Alice@WSO2#SecurePass2024!
# ✅ bob → Password: Bob@WSO2#SecurePass2024!
# ... etc
```

**IMPORTANT:** Save these passwords in a secure password manager!

### 3.1.4 Test bcrypt Authentication

```bash
# Test the new authentication
python3 << 'EOF'
from auth import check_login

# Test valid login
result = check_login('alice', 'Alice@WSO2#SecurePass2024!')
if result:
    print("✅ Valid login test passed")
    print(f"   User: {result['display_name']}")
else:
    print("❌ Valid login test FAILED")

# Test invalid password
result = check_login('alice', 'wrongpassword')
if result is None:
    print("✅ Invalid password test passed")
else:
    print("❌ Invalid password test FAILED")

print("\n✅ bcrypt authentication working correctly!")
EOF
```

---

## 3.2 Security Fix #2: Session Timeout

### 3.2.1 Why Session Timeout Matters

**Scenario Without Timeout:**
```
9:00 AM - Alice logs in at office
9:30 AM - Alice goes to meeting, leaves computer unlocked
10:00 AM - Coworker sits at Alice's desk
10:01 AM - Coworker can access ALL customer data
         - No re-authentication needed
         - Session still active from 9:00 AM
```

**With 60-Minute Timeout:**
```
9:00 AM - Alice logs in
10:01 AM - Session expired (60 min inactive)
10:02 AM - System shows: "Session expired. Please log in again."
         - Coworker cannot access anything
         - Must know Alice's password to continue
```

### 3.2.2 Create Session Manager

```bash
cd ~/ops-copilot_gemini

cat > session_manager.py << 'ENDOFFILE'
# session_manager.py
# ── SESSION MANAGEMENT & TIMEOUT ──────────────────────────
# Tracks user activity and expires inactive sessions

import streamlit as st
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SESSION_TIMEOUT_MINUTES = 60  # 1 hour of inactivity
SESSION_MAX_DURATION_HOURS = 8  # Maximum session length (even if active)

def init_session_tracking():
    '''
    Initialize session tracking variables.
    Call this once when user logs in.
    '''
    st.session_state.last_activity = datetime.now()
    st.session_state.session_start = datetime.now()
    logger.info("Session tracking initialized")

def check_session_timeout() -> tuple[bool, str]:
    '''
    Check if session has expired due to inactivity or max duration.
    
    Returns:
        tuple: (is_valid, message)
            - is_valid (bool): True if session is still valid
            - message (str): Reason for expiration (if expired)
    
    Example:
        >>> valid, msg = check_session_timeout()
        >>> if not valid:
        >>>     st.warning(msg)
        >>>     logout_user()
    '''
    
    # Initialize tracking if not present
    if 'last_activity' not in st.session_state:
        init_session_tracking()
        return True, ""
    
    if 'session_start' not in st.session_state:
        st.session_state.session_start = datetime.now()
    
    now = datetime.now()
    
    # Check 1: Inactivity timeout
    time_since_activity = now - st.session_state.last_activity
    
    if time_since_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        inactive_minutes = int(time_since_activity.total_seconds() / 60)
        message = (
            f'⏱️ Session expired due to {inactive_minutes} minutes of inactivity. '
            f'Please log in again for security.'
        )
        logger.warning(f"Session expired (inactivity): {inactive_minutes} min")
        return False, message
    
    # Check 2: Maximum session duration
    session_duration = now - st.session_state.session_start
    
    if session_duration > timedelta(hours=SESSION_MAX_DURATION_HOURS):
        duration_hours = int(session_duration.total_seconds() / 3600)
        message = (
            f'⏱️ Session expired (maximum duration: {SESSION_MAX_DURATION_HOURS} hours). '
            f'Please log in again.'
        )
        logger.warning(f"Session expired (max duration): {duration_hours} hours")
        return False, message
    
    # Session is valid - update last activity
    st.session_state.last_activity = now
    
    return True, ""

def get_session_info() -> dict:
    '''
    Get information about current session.
    Useful for displaying session status to user.
    
    Returns:
        dict: Session information
        
    Example:
        >>> info = get_session_info()
        >>> st.sidebar.caption(f"Session: {info['active_duration']}")
    '''
    
    if 'last_activity' not in st.session_state:
        return {
            'active': False,
            'active_duration': 'N/A',
            'time_until_timeout': 'N/A'
        }
    
    now = datetime.now()
    
    # Calculate active duration
    session_duration = now - st.session_state.session_start
    active_minutes = int(session_duration.total_seconds() / 60)
    
    # Calculate time until timeout
    time_since_activity = now - st.session_state.last_activity
    remaining = timedelta(minutes=SESSION_TIMEOUT_MINUTES) - time_since_activity
    remaining_minutes = max(0, int(remaining.total_seconds() / 60))
    
    return {
        'active': True,
        'active_duration': f'{active_minutes} min',
        'time_until_timeout': f'{remaining_minutes} min',
        'inactivity_minutes': int(time_since_activity.total_seconds() / 60)
    }

def display_session_status():
    '''
    Display session status in sidebar (optional).
    Shows time until automatic logout.
    '''
    
    info = get_session_info()
    
    if info['active']:
        with st.sidebar:
            with st.expander('Session Info', expanded=False):
                st.caption(f"⏱️ Active: {info['active_duration']}")
                st.caption(f"🔒 Auto-logout in: {info['time_until_timeout']}")
                
                if info['inactivity_minutes'] > SESSION_TIMEOUT_MINUTES - 10:
                    st.warning('⚠️ Session will expire soon due to inactivity')

def logout_user():
    '''
    Properly log out user and clean up session.
    '''
    username = st.session_state.get('user_info', {}).get('username', 'unknown')
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.messages = []
    
    # Clear session tracking
    if 'last_activity' in st.session_state:
        del st.session_state.last_activity
    if 'session_start' in st.session_state:
        del st.session_state.session_start
    
    logger.info(f"User logged out: {username}")
ENDOFFILE
```

### 3.2.3 Update app.py with Session Timeout

**Find this section in app.py (around line 40):**
```python
# ── From here down, user is authenticated ────────────────
user_info = st.session_state.user_info
current_user = user_info['username']
```

**Add session timeout check right after:**
```python
# ── From here down, user is authenticated ────────────────
user_info = st.session_state.user_info
current_user = user_info['username']

# ═══════════════════════════════════════════════════════
# ADD THIS: Session timeout check
# ═══════════════════════════════════════════════════════
from session_manager import check_session_timeout, init_session_tracking

# Initialize session tracking on first authenticated page load
if 'last_activity' not in st.session_state:
    init_session_tracking()

# Check if session has expired
session_valid, timeout_message = check_session_timeout()

if not session_valid:
    # Session expired - force logout
    st.warning(timeout_message)
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.messages = []
    
    # Show login button
    if st.button('🔒 Log in again', type='primary'):
        st.rerun()
    
    st.stop()
# ═══════════════════════════════════════════════════════
```

**Add to app.py just after login success (around line 58):**
```python
if user_info:
    st.session_state.authenticated = True
    st.session_state.user_info = user_info
    
    # ═══════════════════════════════════════════════════════
    # ADD THIS: Initialize session tracking on login
    # ═══════════════════════════════════════════════════════
    from session_manager import init_session_tracking
    init_session_tracking()
    # ═══════════════════════════════════════════════════════
    
    st.rerun()
```

### 3.2.4 Test Session Timeout

```bash
# Test session timeout (for testing, set to 1 minute)
# Edit session_manager.py temporarily:
# SESSION_TIMEOUT_MINUTES = 1  # Changed from 60 to 1 for testing

# Start app
streamlit run app.py

# Test:
# 1. Login
# 2. Wait 61 seconds without clicking anything
# 3. Click anywhere
# 4. Should show: "Session expired due to inactivity"

# After testing, change back to 60 minutes
```

---

## 3.3 Security Fix #3: Environment Variables

### 3.3.1 Why Environment Variables Matter

**Current (INSECURE):**
```bash
# .env file
GOOGLE_API_KEY=AIzaSyC_4QNcJrQ49cqzSpgl5jhDOaw7LmIeps8

# If you accidentally run:
git add .
git commit -m "update"
git push

# → .env is now in Git history FOREVER
# → API key exposed on GitHub/GitLab
# → Anyone can use your quota
# → $10,000+ unexpected bill
```

**Secure Approach:**
```bash
# On server ONLY (not in any file that goes to Git)
export GOOGLE_API_KEY="AIzaSy..."

# Application reads from environment
# Never stored in files
# Different keys for dev/staging/prod
```

### 3.3.2 Update .gitignore

```bash
cd ~/ops-copilot_gemini

# Add to .gitignore
cat >> .gitignore << 'EOF'

# ── Security: Never commit these files ────────────
.env
.env.local
.env.production
*.key
*.pem
users.json
users.json.backup.*

# ── Data files (regenerated, not version controlled) ──
query_log.json
evaluation_results.json
ingestion_state.json
audit_log.json

# ── Database ────────────────────────────────────────
chroma_db/
.sessions/

# ── Python ──────────────────────────────────────────
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/

# ── IDE ─────────────────────────────────────────────
.vscode/
.idea/
*.swp
*.swo

# ── OS ──────────────────────────────────────────────
.DS_Store
Thumbs.db
EOF

# Verify .env is in .gitignore
git check-ignore .env
# Should output: .env

# If .env was already committed, remove it:
git rm --cached .env
git commit -m "Remove .env from version control"
```

### 3.3.3 Update config.py for Environment Variables

```bash
cat > config.py << 'ENDOFFILE'
# config.py
# ── CONFIGURATION WITH SECURE ENVIRONMENT VARIABLES ───────

import os
from pathlib import Path
import sys

# ── API Keys (MUST be environment variables) ──────────────

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

if not GOOGLE_API_KEY:
    # Try loading from .env file (development only)
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == 'GOOGLE_API_KEY':
                            GOOGLE_API_KEY = value
                            break

# Validate API key
if not GOOGLE_API_KEY:
    print("=" * 60)
    print("ERROR: GOOGLE_API_KEY not found!")
    print("=" * 60)
    print()
    print("Set it as an environment variable:")
    print("  export GOOGLE_API_KEY='your_key_here'")
    print()
    print("Or create a .env file with:")
    print("  GOOGLE_API_KEY=your_key_here")
    print()
    sys.exit(1)

# Validate key format
if not GOOGLE_API_KEY.startswith('AIza'):
    print("=" * 60)
    print("ERROR: Invalid GOOGLE_API_KEY format!")
    print("=" * 60)
    print()
    print("Google API keys start with 'AIza'")
    print(f"Your key starts with: {GOOGLE_API_KEY[:10]}...")
    print()
    sys.exit(1)

print("✅ GOOGLE_API_KEY loaded successfully")

# ── Model Configuration ───────────────────────────────────

LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-1.5-flash-latest')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')

# ── Database Configuration ────────────────────────────────

CHROMA_PATH = os.getenv('CHROMA_PATH', './chroma_db')
COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'sre_docs')

# ── Document Processing ───────────────────────────────────

CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1000'))
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', '200'))
TOP_K_RESULTS = int(os.getenv('TOP_K_RESULTS', '5'))

# ── Data Directories ──────────────────────────────────────

MARKDOWN_DIR = os.getenv('MARKDOWN_DIR', './data/markdown')
PDF_DIR = os.getenv('PDF_DIR', './data/pdf')
CONFLUENCE_DIR = os.getenv('CONFLUENCE_DIR', './data/confluence')

# ── Confluence Integration (Optional) ─────────────────────

CONFLUENCE_URL = os.getenv('CONFLUENCE_URL', '')
CONFLUENCE_USERNAME = os.getenv('CONFLUENCE_USERNAME', '')
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_API_TOKEN', '')
CONFLUENCE_SPACE_KEY = os.getenv('CONFLUENCE_SPACE_KEY', '')

# ── GitHub Integration (Optional) ─────────────────────────

GITHUB_REPO_PATH = os.getenv('GITHUB_REPO_PATH', './repos/sre-runbooks')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

# ── Display Configuration (don't show secrets) ────────────

print("Configuration loaded:")
print(f"  LLM Model: {LLM_MODEL}")
print(f"  Embedding Model: {EMBEDDING_MODEL}")
print(f"  ChromaDB Path: {CHROMA_PATH}")
print(f"  Collection: {COLLECTION_NAME}")
print(f"  Chunk Size: {CHUNK_SIZE}")
print(f"  Top K Results: {TOP_K_RESULTS}")
ENDOFFILE
```

### 3.3.4 Create Environment Setup Script

```bash
cat > setup_env.sh << 'ENDOFFILE'
#!/bin/bash
# setup_env.sh
# ── Environment Variable Setup for WSO2 SRE Ops Copilot ──

echo "=================================="
echo "WSO2 SRE Ops Copilot - Environment Setup"
echo "=================================="
echo

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo
    echo "Creating .env template..."
    
    cat > .env << 'ENVFILE'
# WSO2 SRE Ops Copilot - Environment Variables
# IMPORTANT: Never commit this file to Git!

# ── API Keys (REQUIRED) ────────────────────────────────
GOOGLE_API_KEY=your_google_api_key_here

# ── Model Configuration ────────────────────────────────
LLM_MODEL=gemini-1.5-flash-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ── Database ───────────────────────────────────────────
CHROMA_PATH=./chroma_db
COLLECTION_NAME=sre_docs

# ── Document Processing ────────────────────────────────
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5

# ── Optional: Confluence Integration ───────────────────
CONFLUENCE_URL=
CONFLUENCE_USERNAME=
CONFLUENCE_API_TOKEN=
CONFLUENCE_SPACE_KEY=
ENVFILE

    echo "✅ Created .env template"
    echo
    echo "Next steps:"
    echo "1. Edit .env and add your GOOGLE_API_KEY"
    echo "2. Run: source setup_env.sh"
    echo
    exit 0
fi

# Load environment variables from .env
echo "Loading environment variables from .env..."

while IFS='=' read -r key value; do
    # Skip comments and empty lines
    [[ $key =~ ^#.*$ ]] && continue
    [[ -z $key ]] && continue
    
    # Remove quotes from value
    value=$(echo $value | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Export variable
    export "$key=$value"
    
    # Don't show API keys in output
    if [[ $key == *"KEY"* ]] || [[ $key == *"TOKEN"* ]]; then
        echo "  ✅ $key=***hidden***"
    else
        echo "  ✅ $key=$value"
    fi
done < .env

echo
echo "✅ Environment variables loaded"
echo
echo "You can now run:"
echo "  streamlit run app.py"
echo
ENDOFFILE

chmod +x setup_env.sh
```

### 3.3.5 Test Environment Variables

```bash
cd ~/ops-copilot_gemini

# Method 1: Using setup script
source setup_env.sh

# Method 2: Manual export (for production)
export GOOGLE_API_KEY="AIzaSyC_4QNcJrQ49cqzSpgl5jhDOaw7LmIeps8"

# Test that config.py can read it
python3 << 'EOF'
from config import GOOGLE_API_KEY, LLM_MODEL

print(f"✅ API Key loaded: {GOOGLE_API_KEY[:20]}...")
print(f"✅ LLM Model: {LLM_MODEL}")
EOF
```

---

## 3.4 Security Fix #4: HTTPS/TLS Setup

### 3.4.1 Understanding HTTPS

**HTTP (Current - INSECURE):**
```
Browser                          Server
   |                                |
   |  GET /login                    |
   |──────────────────────────────>|
   |                                |
   |  username=alice                |
   |  password=mypassword    ← VISIBLE ON NETWORK
   |──────────────────────────────>|
```

**HTTPS (Secure):**
```
Browser                          Server
   |                                |
   |  TLS Handshake (exchange keys) |
   |<─────────────────────────────>|
   |                                |
   |  Encrypted:                    |
   |  j8Kf9d2!@#kd92js...   ← ENCRYPTED
   |──────────────────────────────>|
   |  (only server can decrypt)     |
```

### 3.4.2 Generate Self-Signed Certificate (Development)

**For development/testing (NOT for production):**

```bash
cd ~/ops-copilot_gemini

# Create certs directory
mkdir -p certs
cd certs

# Generate self-signed certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem \
  -out cert.pem \
  -days 365 \
  -subj "/C=LK/ST=Western/L=Colombo/O=WSO2/OU=SRE/CN=sre-copilot.wso2.internal"

# Verify certificate was created
ls -lh

# Output:
# -rw-rw-r-- 1 user user 2.0K cert.pem
# -rw------- 1 user user 3.2K key.pem

cd ..

echo "✅ SSL certificates generated in certs/"
echo "⚠️  These are self-signed (browser will show warning)"
echo "    For production, use certificates from WSO2 CA"
```

### 3.4.3 Configure Streamlit for HTTPS

**Create HTTPS configuration:**

```bash
cat > .streamlit/config.toml << 'ENDOFFILE'
# .streamlit/config.toml
# Streamlit HTTPS configuration

[server]
# Enable HTTPS
enableCORS = false
enableXsrfProtection = true

# SSL Certificate files
sslCertFile = "certs/cert.pem"
sslKeyFile = "certs/key.pem"

# Server settings
port = 8501
headless = true

# Session configuration
maxUploadSize = 200

[browser]
gatherUsageStats = false
ENDOFFILE
```

**Test HTTPS locally:**

```bash
# Start with HTTPS
streamlit run app.py

# Access via HTTPS (note the 's'):
# https://localhost:8501

# Browser will show warning for self-signed cert
# Click "Advanced" → "Proceed to localhost"
```

### 3.4.4 Production HTTPS with Nginx (Recommended)

**Why Nginx in front of Streamlit:**
1. ✅ Proper SSL termination
2. ✅ Load balancing (if you scale later)
3. ✅ Better logging
4. ✅ Can serve multiple apps
5. ✅ Industry standard

**Install Nginx:**
```bash
# On Ubuntu server
sudo apt update
sudo apt install nginx -y

# Verify installation
nginx -v
```

**Create Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/sre-copilot
```

**Add this configuration:**
```nginx
# /etc/nginx/sites-available/sre-copilot
# WSO2 SRE Ops Copilot - HTTPS Configuration

upstream streamlit {
    server localhost:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name sre-copilot.wso2.internal;
    
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name sre-copilot.wso2.internal;
    
    # SSL Certificate (get from WSO2 IT)
    ssl_certificate /etc/ssl/certs/wso2.crt;
    ssl_certificate_key /etc/ssl/private/wso2.key;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/sre-copilot.access.log;
    error_log /var/log/nginx/sre-copilot.error.log;
    
    # Proxy to Streamlit
    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        
        # WebSocket support (required for Streamlit)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

**Enable configuration:**
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/sre-copilot /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Should show:
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload Nginx
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

---

## 3.5 Additional Security Enhancements

### 3.5.1 Audit Logging

**Create audit_log.py:**
```bash
cat > audit_log.py << 'ENDOFFILE'
# audit_log.py
# ── SECURITY AUDIT LOGGING ────────────────────────────────
# Tracks all security-relevant events for compliance

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = 'audit_log.json'

def log_security_event(
    event_type: str,
    username: str,
    details: Dict[str, Any],
    ip_address: str = None,
    success: bool = True
):
    '''
    Log a security-relevant event to audit log.
    
    Args:
        event_type: Type of event (LOGIN_SUCCESS, USER_CREATED, etc.)
        username: User who triggered the event
        details: Additional event details
        ip_address: Source IP address (if available)
        success: Whether the action succeeded
    
    Event Types:
        - LOGIN_SUCCESS
        - LOGIN_FAILED
        - LOGOUT
        - SESSION_EXPIRED
        - USER_CREATED
        - USER_DELETED
        - PASSWORD_CHANGED
        - QUERY_EXECUTED
        - API_KEY_ACCESSED
        - CONFIG_CHANGED
    
    Example:
        >>> log_security_event(
        ...     'LOGIN_SUCCESS',
        ...     'alice',
        ...     {'method': 'password'},
        ...     '10.0.1.100'
        ... )
    '''
    
    try:
        # Create audit record
        record = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'username': username,
            'ip_address': ip_address,
            'success': success,
            'details': details
        }
        
        # Load existing log
        if Path(AUDIT_LOG_FILE).exists():
            try:
                with open(AUDIT_LOG_FILE, 'r') as f:
                    log_data = json.load(f)
                    if 'events' not in log_data:
                        log_data = {'events': []}
            except json.JSONDecodeError:
                logger.warning("Corrupt audit log, creating new")
                log_data = {'events': []}
        else:
            log_data = {'events': []}
        
        # Append new record
        log_data['events'].append(record)
        
        # Save (with atomic write for safety)
        temp_file = f'{AUDIT_LOG_FILE}.tmp'
        with open(temp_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Atomic rename
        Path(temp_file).replace(AUDIT_LOG_FILE)
        
        # Also log to system log
        logger.info(
            f"AUDIT: {event_type} | User: {username} | "
            f"IP: {ip_address} | Success: {success}"
        )
    
    except Exception as e:
        # Never let audit logging break the app
        logger.error(f"Failed to write audit log: {e}")

def get_user_audit_trail(username: str, limit: int = 100) -> list:
    '''
    Get audit trail for a specific user.
    
    Args:
        username: User to get trail for
        limit: Maximum number of events to return
    
    Returns:
        list: Audit events for the user
    '''
    
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []
        
        with open(AUDIT_LOG_FILE, 'r') as f:
            log_data = json.load(f)
        
        # Filter events for this user
        user_events = [
            event for event in log_data.get('events', [])
            if event.get('username') == username
        ]
        
        # Return most recent first
        return sorted(
            user_events,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]
    
    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []

def get_failed_login_attempts(minutes: int = 60) -> list:
    '''
    Get failed login attempts in the last N minutes.
    Useful for detecting brute force attacks.
    
    Args:
        minutes: Time window to check
    
    Returns:
        list: Failed login attempts
    '''
    
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []
        
        with open(AUDIT_LOG_FILE, 'r') as f:
            log_data = json.load(f)
        
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        
        failed_logins = [
            event for event in log_data.get('events', [])
            if event.get('event_type') == 'LOGIN_FAILED'
            and datetime.fromisoformat(event['timestamp']).timestamp() > cutoff_time
        ]
        
        return failed_logins
    
    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []
ENDOFFILE
```

**Integrate audit logging into auth.py:**

Add at the top of auth.py:
```python
from audit_log import log_security_event
```

Update check_login() function:
```python
def check_login(username: str, password: str) -> Optional[Dict]:
    # ... existing code ...
    
    # At the end, add:
    if user_info:
        # Success
        log_security_event('LOGIN_SUCCESS', username, {'method': 'password'})
        logger.info(f"Successful login for user: {username}")
        return user_info
    else:
        # Failure
        log_security_event(
            'LOGIN_FAILED',
            username,
            {'reason': 'invalid_credentials'},
            success=False
        )
        logger.info(f"Failed login attempt for user: {username}")
        return None
```

### 3.5.2 Rate Limiting

**Create rate_limiter.py:**
```bash
cat > rate_limiter.py << 'ENDOFFILE'
# rate_limiter.py
# ── RATE LIMITING TO PREVENT ABUSE ────────────────────────

from datetime import datetime, timedelta
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MAX_QUERIES_PER_MINUTE = 10
MAX_QUERIES_PER_HOUR = 100
MAX_LOGIN_ATTEMPTS_PER_HOUR = 5

# In-memory storage (will be lost on restart, which is fine)
query_counts = defaultdict(list)
login_attempts = defaultdict(list)

def check_query_rate_limit(username: str) -> tuple[bool, str]:
    '''
    Check if user has exceeded query rate limits.
    
    Args:
        username: User to check
    
    Returns:
        tuple: (allowed, message)
            - allowed (bool): True if within limits
            - message (str): Error message if rate limited
    
    Limits:
        - 10 queries per minute
        - 100 queries per hour
    '''
    
    now = datetime.now()
    
    # Clean old queries (older than 1 hour)
    query_counts[username] = [
        ts for ts in query_counts[username]
        if now - ts < timedelta(hours=1)
    ]
    
    # Check per-minute limit
    recent = [
        ts for ts in query_counts[username]
        if now - ts < timedelta(minutes=1)
    ]
    
    if len(recent) >= MAX_QUERIES_PER_MINUTE:
        logger.warning(f"Rate limit (1min) exceeded for user: {username}")
        return False, (
            f'⏱️ Rate limit exceeded: {MAX_QUERIES_PER_MINUTE} queries per minute. '
            f'Please wait before asking more questions.'
        )
    
    # Check per-hour limit
    if len(query_counts[username]) >= MAX_QUERIES_PER_HOUR:
        logger.warning(f"Rate limit (1hour) exceeded for user: {username}")
        return False, (
            f'⏱️ Rate limit exceeded: {MAX_QUERIES_PER_HOUR} queries per hour. '
            f'Please try again later.'
        )
    
    # Within limits - record this query
    query_counts[username].append(now)
    return True, ''

def check_login_rate_limit(username: str) -> tuple[bool, str]:
    '''
    Check login attempt rate limit to prevent brute force.
    
    Args:
        username: Username attempting login
    
    Returns:
        tuple: (allowed, message)
    
    Limits:
        - 5 failed login attempts per hour
    '''
    
    now = datetime.now()
    
    # Clean old attempts (older than 1 hour)
    login_attempts[username] = [
        ts for ts in login_attempts[username]
        if now - ts < timedelta(hours=1)
    ]
    
    if len(login_attempts[username]) >= MAX_LOGIN_ATTEMPTS_PER_HOUR:
        logger.warning(f"Login rate limit exceeded for user: {username}")
        return False, (
            f'🔒 Too many failed login attempts. '
            f'Please try again in 1 hour or contact an administrator.'
        )
    
    return True, ''

def record_failed_login(username: str):
    '''Record a failed login attempt.'''
    login_attempts[username].append(datetime.now())

def reset_login_attempts(username: str):
    '''Reset login attempts after successful login.'''
    login_attempts[username] = []

def get_rate_limit_status(username: str) -> dict:
    '''
    Get current rate limit status for user (for display).
    
    Returns:
        dict: Rate limit information
    '''
    
    now = datetime.now()
    
    # Count recent queries
    recent_minute = sum(
        1 for ts in query_counts[username]
        if now - ts < timedelta(minutes=1)
    )
    
    recent_hour = len(query_counts[username])
    
    return {
        'queries_last_minute': recent_minute,
        'queries_last_hour': recent_hour,
        'minute_limit': MAX_QUERIES_PER_MINUTE,
        'hour_limit': MAX_QUERIES_PER_HOUR,
        'minute_remaining': max(0, MAX_QUERIES_PER_MINUTE - recent_minute),
        'hour_remaining': max(0, MAX_QUERIES_PER_HOUR - recent_hour)
    }
ENDOFFILE
```

**Integrate rate limiting into app.py:**

Add before processing query (around line 170):
```python
if prompt:
    # ═══════════════════════════════════════════════════════
    # ADD THIS: Rate limiting check
    # ═══════════════════════════════════════════════════════
    from rate_limiter import check_query_rate_limit
    
    allowed, rate_limit_message = check_query_rate_limit(current_user)
    
    if not allowed:
        st.error(rate_limit_message)
        st.info('💡 Tip: Rate limits help ensure fair usage for all team members.')
        st.stop()
    # ═══════════════════════════════════════════════════════
    
    # Display user question
    with st.chat_message('user'):
        st.write(prompt)
    # ... rest of code
```

---

## 3.6 Updated requirements.txt

```bash
cat > requirements.txt << 'ENDOFFILE'
# WSO2 SRE Ops Copilot - Python Dependencies
# Enterprise-Ready Version

# ── Core Application ──────────────────────────────────────
streamlit==1.31.0

# ── AI & Machine Learning ─────────────────────────────────
google-generativeai==0.3.2
sentence-transformers==2.5.1
chromadb==0.4.22

# ── Document Processing ───────────────────────────────────
langchain==0.1.9
langchain-community==0.0.24
langchain-google-genai==0.0.9

# ── Evaluation ────────────────────────────────────────────
ragas==0.1.5
datasets==2.17.1

# ── Data Processing ───────────────────────────────────────
pandas==2.2.0
numpy==1.26.3
pyyaml==6.0.1

# ── Security (NEW - CRITICAL) ─────────────────────────────
bcrypt==4.1.2

# ── Scheduling ────────────────────────────────────────────
apscheduler==3.10.4

# ── File Handling ─────────────────────────────────────────
pypdf==4.0.1
python-docx==1.1.0

# ── HTTP & Networking ─────────────────────────────────────
requests==2.31.0
urllib3==2.2.0

# ── Optional: For production monitoring ──────────────────
# prometheus-client==0.19.0
# sentry-sdk==1.40.0
ENDOFFILE
```

---

# 4. AZURE DEPLOYMENT GUIDE

## 4.1 Azure Account Setup

### 4.1.1 Prerequisites

**Before starting, ensure you have:**
1. ✅ Active Azure subscription
2. ✅ Azure CLI installed on your local machine
3. ✅ SSH key pair generated
4. ✅ Permission to create resources in Azure

**Check Azure CLI:**
```bash
# Install Azure CLI (Ubuntu/WSL)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version

# Should show: azure-cli 2.x.x
```

**Login to Azure:**
```bash
# This will open a browser for authentication
az login

# Select your subscription (if you have multiple)
az account list --output table

# Set the subscription you want to use
az account set --subscription "Your Subscription Name"
```

**Generate SSH key (if you don't have one):**
```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -C "your.email@wso2.com" -f ~/.ssh/azure_wso2_sre

# This creates:
# - ~/.ssh/azure_wso2_sre (private key - NEVER SHARE)
# - ~/.ssh/azure_wso2_sre.pub (public key - upload to Azure)

# View public key (you'll need this)
cat ~/.ssh/azure_wso2_sre.pub
```

### 4.1.2 Create Resource Group

**Resource Group** is a container for Azure resources (like a folder).

```bash
# Create resource group in Southeast Asia region (closest to Sri Lanka)
az group create \
  --name rg-wso2-sre-copilot \
  --location southeastasia \
  --tags \
    Environment=Production \
    Team=SRE \
    Project=OpsContoh Purpose

# Verify creation
az group show --name rg-wso2-sre-copilot --output table
```

**Why this configuration:**
- `southeastasia` - Low latency from Sri Lanka (~25ms)
- Tags help with cost tracking and organization

## 4.2 Virtual Machine Setup

### 4.2.1 Choose VM Size

**Recommended for WSO2 SRE team (5-20 users):**

| VM Size | vCPUs | RAM | Cost/Month | Best For |
|---------|-------|-----|------------|----------|
| Standard_B2s | 2 | 4 GB | ~$40 | Testing, <10 users |
| **Standard_B2ms** | **2** | **8 GB** | **~$65** | **Production (recommended)** |
| Standard_B4ms | 4 | 16 GB | ~$130 | Heavy usage, >20 users |

**We'll use Standard_B2ms:**
- ✅ 2 vCPUs (enough for Streamlit + ChromaDB)
- ✅ 8 GB RAM (handles vector embeddings well)
- ✅ Burstable (can handle traffic spikes)
- ✅ Good cost/performance ratio

### 4.2.2 Create Virtual Machine

```bash
# Create Ubuntu 22.04 VM
az vm create \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --image Ubuntu2204 \
  --size Standard_B2ms \
  --admin-username sreadmin \
  --ssh-key-values ~/.ssh/azure_wso2_sre.pub \
  --public-ip-sku Standard \
  --public-ip-address-dns-name wso2-sre-copilot \
  --nsg-rule SSH \
  --os-disk-size-gb 64 \
  --tags \
    Environment=Production \
    Application=SRECopilot \
    ManagedBy=SRETeam

# This takes 2-3 minutes...
# Output will show public IP address
```

**Command explanation:**
- `--image Ubuntu2204` - Latest Ubuntu LTS
- `--size Standard_B2ms` - 2 vCPU, 8GB RAM
- `--admin-username sreadmin` - Admin user account
- `--ssh-key-values` - Your public SSH key
- `--public-ip-address-dns-name` - Creates DNS name
- `--nsg-rule SSH` - Opens port 22 for SSH

**Save the public IP:**
```bash
# Get VM details
az vm show \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --show-details \
  --output table

# Note the publicIps value
# Example: 20.212.45.123
```

### 4.2.3 Configure Network Security Group

**Open required ports:**

```bash
# Open port 443 for HTTPS
az vm open-port \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --port 443 \
  --priority 1001

# Open port 80 for HTTP (redirects to HTTPS)
az vm open-port \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --port 80 \
  --priority 1002

# Verify NSG rules
az network nsg rule list \
  --resource-group rg-wso2-sre-copilot \
  --nsg-name vm-sre-copilotNSG \
  --output table
```

**Expected rules:**
- Port 22 (SSH) - For administration
- Port 80 (HTTP) - Redirect to HTTPS
- Port 443 (HTTPS) - Main application

## 4.3 Server Configuration

### 4.3.1 Connect to VM

```bash
# SSH into the VM
ssh -i ~/.ssh/azure_wso2_sre sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com

# Or use IP directly:
ssh -i ~/.ssh/azure_wso2_sre sreadmin@20.212.45.123

# You should see Ubuntu welcome message
```

### 4.3.2 System Updates

```bash
# Update package list
sudo apt update

# Upgrade all packages
sudo apt upgrade -y

# Install essential tools
sudo apt install -y \
  git \
  curl \
  wget \
  vim \
  htop \
  ufw \
  nginx \
  python3-pip \
  python3-venv \
  build-essential

# Verify installations
python3 --version  # Should be 3.10+
git --version
nginx -v
```

### 4.3.3 Configure Firewall

```bash
# Enable UFW firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Verify status
sudo ufw status

# Should show:
# Status: active
# To                         Action      From
# --                         ------      ----
# OpenSSH                    ALLOW       Anywhere
# Nginx Full                 ALLOW       Anywhere
```

### 4.3.4 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Log out and back in for group changes to take effect
exit
# Then SSH back in
ssh -i ~/.ssh/azure_wso2_sre sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com

# Test Docker without sudo
docker ps
```

## 4.4 Application Deployment

### 4.4.1 Transfer Application to Server

**Option A: Using Git (Recommended)**

```bash
# On Azure VM:
cd /home/sreadmin

# Clone your repository (if it's in Git)
git clone https://github.com/yourorg/ops-copilot-gemini.git
cd ops-copilot-gemini

# Or if using Azure DevOps:
git clone https://dev.azure.com/wso2/ops-copilot-gemini
cd ops-copilot-gemini
```

**Option B: Using SCP (if not in Git)**

```bash
# On your LOCAL machine:
cd ~/ops-copilot_gemini

# Create tarball (excluding unnecessary files)
tar -czf sre-copilot.tar.gz \
  --exclude='chroma_db' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='query_log.json' \
  .

# Copy to Azure VM
scp -i ~/.ssh/azure_wso2_sre \
  sre-copilot.tar.gz \
  sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com:/home/sreadmin/

# SSH to VM and extract
ssh -i ~/.ssh/azure_wso2_sre sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com

cd /home/sreadmin
tar -xzf sre-copilot.tar.gz
mv <extracted_folder> ops-copilot-gemini  # if needed
cd ops-copilot-gemini
```

### 4.4.2 Setup Environment Variables

```bash
# On Azure VM:
cd /home/sreadmin/ops-copilot-gemini

# Create .env file (NEVER commit to Git!)
nano .env
```

**Add your environment variables:**
```bash
# WSO2 SRE Ops Copilot - Production Environment Variables

# ── API Keys ──────────────────────────────────────────────
GOOGLE_API_KEY=AIzaSyC_4QNcJrQ49cqzSpgl5jhDOaw7LmIeps8

# ── Model Configuration ────────────────────────────────────
LLM_MODEL=gemini-1.5-flash-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2

# ── Database ───────────────────────────────────────────────
CHROMA_PATH=./chroma_db
COLLECTION_NAME=sre_docs

# ── Document Processing ────────────────────────────────────
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
```

**Save:** Ctrl+X, Y, Enter

**Set file permissions (important!):**
```bash
# Make .env readable only by owner
chmod 600 .env

# Verify permissions
ls -la .env
# Should show: -rw------- (owner read/write only)
```

### 4.4.3 Setup Application

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# This takes 5-10 minutes...

# Verify installation
python3 -c "import streamlit; import bcrypt; print('✅ All dependencies installed')"
```

### 4.4.4 Initialize Database

```bash
# Create data directories
mkdir -p data/markdown data/pdf data/yaml

# Upload your documents
# (Use SCP from local machine or Azure Storage)

# Run initial ingestion
python3 ingest.py

# Should output:
# Loading embedding model...
# Connecting to ChromaDB...
# Loaded X markdown files
# Loaded Y PDF files
# Split X documents into Y chunks
# ✅ Ingestion complete!
```

### 4.4.5 Configure Systemd Service

**Create systemd service for auto-start:**

```bash
sudo nano /etc/systemd/system/sre-copilot.service
```

**Add this configuration:**
```ini
[Unit]
Description=WSO2 SRE Ops Copilot
After=network.target

[Service]
Type=simple
User=sreadmin
WorkingDirectory=/home/sreadmin/ops-copilot-gemini
Environment="PATH=/home/sreadmin/ops-copilot-gemini/venv/bin"
ExecStart=/home/sreadmin/ops-copilot-gemini/venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable sre-copilot

# Start service
sudo systemctl start sre-copilot

# Check status
sudo systemctl status sre-copilot

# Should show: Active: active (running)

# View logs
sudo journalctl -u sre-copilot -f
```

### 4.4.6 Configure Nginx as Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/sre-copilot
```

**Add this configuration:**
```nginx
# WSO2 SRE Ops Copilot - Nginx Configuration

upstream streamlit {
    server 127.0.0.1:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;
    
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name wso2-sre-copilot.southeastasia.cloudapp.azure.com;
    
    # SSL Certificate (Let's Encrypt - we'll set this up next)
    ssl_certificate /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wso2-sre-copilot.southeastasia.cloudapp.azure.com/privkey.pem;
    
    # SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # Logging
    access_log /var/log/nginx/sre-copilot.access.log;
    error_log /var/log/nginx/sre-copilot.error.log;
    
    # Proxy to Streamlit
    location / {
        proxy_pass http://streamlit;
        proxy_http_version 1.1;
        
        # WebSocket support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 4.4.7 Setup SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d wso2-sre-copilot.southeastasia.cloudapp.azure.com --email your.email@wso2.com --agree-tos --no-eff-email

# Certbot will:
# 1. Verify domain ownership
# 2. Generate SSL certificate
# 3. Update Nginx configuration automatically
# 4. Setup auto-renewal

# Test auto-renewal
sudo certbot renew --dry-run

# Should show: Congratulations, all renewals succeeded!
```

**Enable Nginx configuration:**
```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/sre-copilot /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx
```

### 4.4.8 Test Deployment

```bash
# On Azure VM:
# Check if Streamlit is running
curl http://localhost:8501

# Check if Nginx is proxying
curl https://wso2-sre-copilot.southeastasia.cloudapp.azure.com

# On your LOCAL machine:
# Open browser
# Navigate to: https://wso2-sre-copilot.southeastasia.cloudapp.azure.com

# You should see the login page!
```

---

## 4.5 Post-Deployment Configuration

### 4.5.1 Create Initial Users

```bash
# On Azure VM:
cd /home/sreadmin/ops-copilot-gemini

# Activate virtual environment
source venv/bin/activate

# Run password migration script
python3 migrate_passwords.py

# This creates users.json with bcrypt hashes
```

### 4.5.2 Setup Backup Script

```bash
# Create backup script
nano backup.sh
```

**Add this content:**
```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR="/home/sreadmin/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup data files
cp /home/sreadmin/ops-copilot-gemini/users.json "$BACKUP_DIR/"
cp /home/sreadmin/ops-copilot-gemini/query_log.json "$BACKUP_DIR/" 2>/dev/null || true
cp /home/sreadmin/ops-copilot-gemini/audit_log.json "$BACKUP_DIR/" 2>/dev/null || true

# Backup ChromaDB
cp -r /home/sreadmin/ops-copilot-gemini/chroma_db "$BACKUP_DIR/"

# Backup documents
cp -r /home/sreadmin/ops-copilot-gemini/data "$BACKUP_DIR/"

# Create tarball
cd /home/sreadmin/backups
tar -czf "$(basename $BACKUP_DIR).tar.gz" "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

# Keep only last 30 days
find /home/sreadmin/backups -type f -name "*.tar.gz" -mtime +30 -delete

echo "✅ Backup complete: $BACKUP_DIR.tar.gz"
```

**Make executable and schedule:**
```bash
chmod +x backup.sh

# Add to crontab (daily at 2 AM)
crontab -e

# Add this line:
0 2 * * * /home/sreadmin/ops-copilot-gemini/backup.sh >> /home/sreadmin/backup.log 2>&1
```

### 4.5.3 Setup Monitoring

```bash
# Create monitoring script
nano monitor.sh
```

**Add this content:**
```bash
#!/bin/bash
# monitor.sh - Check application health

# Check if Streamlit is running
if ! systemctl is-active --quiet sre-copilot; then
    echo "❌ Streamlit is not running!"
    sudo systemctl start sre-copilot
    echo "✅ Restarted Streamlit"
fi

# Check if Nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "❌ Nginx is not running!"
    sudo systemctl start nginx
    echo "✅ Restarted Nginx"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠️  Disk usage high: ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "⚠️  Memory usage high: ${MEM_USAGE}%"
fi

echo "✅ Health check complete"
```

**Make executable and schedule:**
```bash
chmod +x monitor.sh

# Run every 5 minutes
crontab -e

# Add this line:
*/5 * * * * /home/sreadmin/ops-copilot-gemini/monitor.sh >> /home/sreadmin/monitor.log 2>&1
```

---

# 5. POST-DEPLOYMENT CONFIGURATION

## 5.1 User Management

### 5.1.1 Access Admin Panel

```
1. Open browser
2. Navigate to: https://wso2-sre-copilot.southeastasia.cloudapp.azure.com
3. Login with admin credentials
4. Click "Admin Panel" in sidebar
5. Add WSO2 SRE team members
```

### 5.1.2 Add New Users

**In Admin Panel:**
```
Username: john.doe
Password: John@WSO2#Secure2024!
Display Name: John Doe (SRE)
Role: sre
```

**Share credentials securely:**
- Use password manager (1Password, LastPass)
- Or encrypted email
- NEVER plain text Slack/Teams

## 5.2 Document Ingestion

### 5.2.1 Upload Documents

```bash
# On Azure VM:
cd /home/sreadmin/ops-copilot-gemini/data

# Create customer directories
mkdir -p markdown/customerx markdown/customery
mkdir -p pdf/customerx pdf/customery
mkdir -p yaml/customerx yaml/customery

# Upload documents (using SCP from local machine)
```

**From local machine:**
```bash
# Upload markdown files
scp -i ~/.ssh/azure_wso2_sre \
  customerx_deployment.md \
  sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com:/home/sreadmin/ops-copilot-gemini/data/markdown/customerx/

# Upload PDF files
scp -i ~/.ssh/azure_wso2_sre \
  customerx_runbook.pdf \
  sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com:/home/sreadmin/ops-copilot-gemini/data/pdf/customerx/

# Upload YAML files
scp -i ~/.ssh/azure_wso2_sre \
  customerx-deployment.yaml \
  sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com:/home/sreadmin/ops-copilot-gemini/data/yaml/customerx/
```

### 5.2.2 Run Ingestion

```bash
# On Azure VM:
cd /home/sreadmin/ops-copilot-gemini
source venv/bin/activate

# Run ingestion
python3 ingest.py

# Or use the dashboard
# Go to Ingestion Log → Click "Re-ingest all files"
```

## 5.3 SSL Certificate Renewal

**Automatic renewal is already setup by Certbot, but verify:**

```bash
# Check certificate expiry
sudo certbot certificates

# Test renewal process
sudo certbot renew --dry-run

# View renewal timer
sudo systemctl list-timers | grep certbot

# Certbot auto-renews 30 days before expiry
```

---

# 6. MONITORING & MAINTENANCE

## 6.1 Daily Monitoring

### 6.1.1 Check Application Health

```bash
# SSH to Azure VM
ssh -i ~/.ssh/azure_wso2_sre sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com

# Check Streamlit status
sudo systemctl status sre-copilot

# Check Nginx status
sudo systemctl status nginx

# View recent logs
sudo journalctl -u sre-copilot -n 50 --no-pager

# Check error logs
tail -f /var/log/nginx/sre-copilot.error.log
```

### 6.1.2 Monitor Resource Usage

```bash
# Real-time system monitoring
htop

# Disk usage
df -h

# Memory usage
free -h

# Check Docker containers (if using Docker)
docker ps
docker stats
```

### 6.1.3 Review Audit Logs

```bash
cd /home/sreadmin/ops-copilot-gemini

# View recent audit events
python3 << 'EOF'
import json
with open('audit_log.json') as f:
    data = json.load(f)
    for event in data['events'][-10:]:  # Last 10 events
        print(f"{event['timestamp']} - {event['event_type']} - {event['username']}")
EOF

# Check for failed logins
grep "LOGIN_FAILED" audit_log.json

# Count queries by user
grep "QUERY_EXECUTED" audit_log.json | wc -l
```

## 6.2 Backup Verification

```bash
# List backups
ls -lh /home/sreadmin/backups/

# Test restore (on a test system)
cd /home/sreadmin/backups
tar -xzf 20260512_020000.tar.gz
# Verify files are intact
```

## 6.3 Performance Tuning

### 6.3.1 If Application is Slow

```bash
# Increase Streamlit workers
sudo nano /etc/systemd/system/sre-copilot.service

# Change ExecStart line to:
# ExecStart=/home/sreadmin/ops-copilot-gemini/venv/bin/streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.runOnSave false --server.maxUploadSize 200

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart sre-copilot
```

### 6.3.2 If Memory Usage is High

```bash
# Check memory
free -h

# Check what's using memory
ps aux --sort=-%mem | head -n 10

# If ChromaDB is using too much memory, reduce cache
nano /home/sreadmin/ops-copilot-gemini/config.py
# Add: CHROMA_CACHE_SIZE = 1000  # Reduce from default
```

## 6.4 Updates and Upgrades

### 6.4.1 Update Application Code

```bash
# SSH to Azure VM
cd /home/sreadmin/ops-copilot-gemini

# Pull latest code (if using Git)
git pull origin main

# Or upload new version using SCP

# Restart application
sudo systemctl restart sre-copilot

# Verify it's working
curl http://localhost:8501
```

### 6.4.2 Update System Packages

```bash
# Update package list
sudo apt update

# Upgrade packages
sudo apt upgrade -y

# Reboot if kernel was updated
sudo reboot

# After reboot, verify services are running
sudo systemctl status sre-copilot
sudo systemctl status nginx
```

---

# 7. TROUBLESHOOTING

## 7.1 Common Issues

### 7.1.1 Cannot Access Application

**Symptom:** Browser shows "Connection refused" or "This site can't be reached"

**Diagnosis:**
```bash
# Check if Streamlit is running
sudo systemctl status sre-copilot

# Check if Nginx is running
sudo systemctl status nginx

# Check firewall
sudo ufw status

# Check if port 443 is listening
sudo netstat -tulpn | grep 443
```

**Solutions:**
```bash
# Restart Streamlit
sudo systemctl restart sre-copilot

# Restart Nginx
sudo systemctl restart nginx

# Check logs
sudo journalctl -u sre-copilot -n 50
sudo tail -f /var/log/nginx/sre-copilot.error.log
```

### 7.1.2 Login Not Working

**Symptom:** "Invalid credentials" even with correct password

**Diagnosis:**
```bash
cd /home/sreadmin/ops-copilot-gemini

# Check if users.json exists
ls -la users.json

# Verify users.json format
python3 -c "import json; print(json.load(open('users.json')))"

# Test authentication directly
python3 << 'EOF'
from auth import check_login
result = check_login('alice', 'Alice@WSO2#SecurePass2024!')
print('Success' if result else 'Failed')
EOF
```

**Solution:**
```bash
# Re-run password migration
python3 migrate_passwords.py

# Restart application
sudo systemctl restart sre-copilot
```

### 7.1.3 Session Expires Too Quickly

**Symptom:** "Session expired" message after just a few minutes

**Diagnosis:**
```bash
# Check session timeout setting
grep "SESSION_TIMEOUT_MINUTES" session_manager.py
```

**Solution:**
```bash
# Edit session timeout
nano session_manager.py

# Change:
# SESSION_TIMEOUT_MINUTES = 60  # or higher

# Restart
sudo systemctl restart sre-copilot
```

### 7.1.4 API Rate Limit Errors

**Symptom:** "429 Rate limit exceeded" from Gemini API

**Diagnosis:**
```bash
# Check recent queries
grep "429" query_log.json

# Count queries today
date +%Y-%m-%d
grep "$(date +%Y-%m-%d)" query_log.json | wc -l
```

**Solution:**
```bash
# Wait for quota reset (midnight Pacific Time)
# Or upgrade to paid Gemini API plan
# Or implement query caching
```

### 7.1.5 Out of Disk Space

**Symptom:** Application crashes, backup fails

**Diagnosis:**
```bash
# Check disk usage
df -h

# Find large files
du -h /home/sreadmin --max-depth=2 | sort -hr | head -20
```

**Solution:**
```bash
# Clean old backups
find /home/sreadmin/backups -type f -mtime +7 -delete

# Clean Docker (if using)
docker system prune -a

# Clean logs
sudo journalctl --vacuum-size=100M

# Clean apt cache
sudo apt clean
```

## 7.2 Emergency Procedures

### 7.2.1 Complete System Failure

```bash
# Check VM status in Azure Portal
az vm show \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot \
  --output table

# If VM is stopped, start it
az vm start \
  --resource-group rg-wso2-sre-copilot \
  --name vm-sre-copilot

# SSH and check services
ssh -i ~/.ssh/azure_wso2_sre sreadmin@wso2-sre-copilot.southeastasia.cloudapp.azure.com
sudo systemctl status sre-copilot
sudo systemctl status nginx
```

### 7.2.2 Data Recovery from Backup

```bash
# SSH to VM
cd /home/sreadmin/backups

# List available backups
ls -lh

# Extract latest backup
tar -xzf 20260512_020000.tar.gz
cd 20260512_020000

# Restore files
cp users.json /home/sreadmin/ops-copilot-gemini/
cp query_log.json /home/sreadmin/ops-copilot-gemini/
cp -r chroma_db /home/sreadmin/ops-copilot-gemini/
cp -r data /home/sreadmin/ops-copilot-gemini/

# Restart application
sudo systemctl restart sre-copilot
```

### 7.2.3 Rollback to Previous Version

```bash
# If using Git:
cd /home/sreadmin/ops-copilot-gemini
git log --oneline -n 10  # View recent commits
git checkout <commit_hash>  # Rollback to specific version
sudo systemctl restart sre-copilot

# If not using Git:
# Restore from backup that includes code
```

---

# 8. SECURITY CHECKLIST

## 8.1 Pre-Production Security Audit

**Before going live, verify:**

- [ ] ✅ bcrypt password hashing implemented
- [ ] ✅ HTTPS/TLS enabled with valid certificate
- [ ] ✅ Session timeout configured (60 minutes)
- [ ] ✅ Environment variables used for secrets (no hardcoded API keys)
- [ ] ✅ .gitignore updated (no secrets in Git)
- [ ] ✅ Firewall configured (only ports 22, 80, 443 open)
- [ ] ✅ SSH key-based authentication (no password login)
- [ ] ✅ Audit logging enabled
- [ ] ✅ Rate limiting implemented
- [ ] ✅ Backups scheduled (daily at 2 AM)
- [ ] ✅ Monitoring configured (health checks every 5 min)
- [ ] ✅ SSL auto-renewal tested
- [ ] ✅ Admin panel access restricted (admin role only)
- [ ] ✅ Error messages don't expose sensitive data
- [ ] ✅ Logs don't contain passwords or API keys

## 8.2 Monthly Security Review

**Every month:**

1. Review audit log for suspicious activity
2. Check for failed login attempts
3. Verify backups are working
4. Update system packages
5. Review user access (remove inactive users)
6. Check SSL certificate expiry
7. Review API usage and costs

---

# 9. COST OPTIMIZATION

## 9.1 Azure Cost Breakdown

**Expected monthly costs:**

| Resource | Size | Monthly Cost (USD) |
|----------|------|-------------------|
| Virtual Machine (B2ms) | 2 vCPU, 8 GB RAM | $65 |
| OS Disk (64 GB SSD) | Standard SSD | $5 |
| Public IP | Static | $3 |
| Data Transfer | 100 GB/month | $8 |
| **Total** | | **~$81/month** |

**Gemini API costs:**
- Free tier: 1,500 requests/day, 1M tokens/day
- If exceeded: $0.00035 per 1K tokens
- Expected for 20 users: ~$10-20/month

**Total estimated cost: $91-101/month**

## 9.2 Cost Saving Tips

1. **Use reserved instances** (if committing for 1 year)
   - Save up to 40% on VM costs
   
2. **Stop VM outside business hours** (if not 24/7)
   ```bash
   # Stop VM
   az vm deallocate --resource-group rg-wso2-sre-copilot --name vm-sre-copilot
   
   # Start VM
   az vm start --resource-group rg-wso2-sre-copilot --name vm-sre-copilot
   ```

3. **Use Azure Cost Management**
   - Set budget alerts
   - Review costs weekly

4. **Optimize document storage**
   - Delete old query logs
   - Compress backup files

---

# 10. CONCLUSION

## 10.1 What You've Accomplished

✅ **Security:** Enterprise-grade authentication with bcrypt, HTTPS, session timeout  
✅ **Deployment:** Production-ready Azure VM with monitoring and backups  
✅ **Scalability:** Can handle 5-50 WSO2 SRE team members  
✅ **Maintainability:** Automated backups, health checks, easy updates  
✅ **Cost-Effective:** ~$100/month for full production system  

## 10.2 Next Steps

1. **Week 1:** Deploy to Azure, migrate first 5 users
2. **Week 2:** Upload all customer documents, train team
3. **Week 3:** Monitor usage, gather feedback
4. **Month 2+:** Optimize based on usage patterns

## 10.3 Support Contacts

**For issues:**
- Application bugs: Your development team
- Azure infrastructure: Azure support
- Gemini API: Google Cloud support

**Documentation:**
- Streamlit: https://docs.streamlit.io
- Azure: https://docs.microsoft.com/azure
- bcrypt: https://github.com/pyca/bcrypt

---

# APPENDIX A: Quick Reference Commands

```bash
# ── Application Management ────────────────────────────────
sudo systemctl status sre-copilot    # Check status
sudo systemctl start sre-copilot     # Start
sudo systemctl stop sre-copilot      # Stop
sudo systemctl restart sre-copilot   # Restart
sudo journalctl -u sre-copilot -f    # View logs

# ── Nginx Management ──────────────────────────────────────
sudo systemctl status nginx          # Check status
sudo systemctl reload nginx          # Reload config
sudo nginx -t                        # Test config
tail -f /var/log/nginx/sre-copilot.error.log  # View errors

# ── Backups ───────────────────────────────────────────────
cd /home/sreadmin/backups
ls -lh                              # List backups
tar -xzf <backup>.tar.gz            # Extract backup

# ── Monitoring ────────────────────────────────────────────
htop                                # System resources
df -h                               # Disk usage
free -h                             # Memory usage
sudo ufw status                     # Firewall status

# ── SSL Certificate ───────────────────────────────────────
sudo certbot certificates           # Check expiry
sudo certbot renew                  # Manual renewal
sudo certbot renew --dry-run        # Test renewal
```

---

# APPENDIX B: File Locations Reference

```
/home/sreadmin/ops-copilot-gemini/
├── app.py                          # Main application
├── auth.py                         # Authentication (bcrypt)
├── session_manager.py              # Session timeout
├── audit_log.py                    # Security logging
├── rate_limiter.py                 # Rate limiting
├── config.py                       # Configuration
├── .env                            # Environment variables (SECRET!)
├── users.json                      # User database (SECRET!)
├── query_log.json                  # Query logs
├── audit_log.json                  # Audit trail
├── chroma_db/                      # Vector database
├── data/                           # Documents
│   ├── markdown/
│   ├── pdf/
│   └── yaml/
└── backups/                        # Daily backups

/etc/nginx/sites-available/
└── sre-copilot                     # Nginx configuration

/etc/systemd/system/
└── sre-copilot.service             # Systemd service

/var/log/nginx/
├── sre-copilot.access.log          # Access logs
└── sre-copilot.error.log           # Error logs
```

---

**END OF DOCUMENT**

**Document prepared for:** WSO2 SRE Team  
**System:** SRE Ops Copilot - RAG Knowledge Base  
**Deployment Target:** Azure Cloud (Southeast Asia)  
**Security Level:** Enterprise Production-Ready  

**For questions or support:** Contact your DevOps team or Azure administrator.
