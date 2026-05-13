# STEP 1 — Upgrade Password Hashing: SHA-256 → bcrypt

## Why This Is Critical

Your current `auth.py` and `pages/5_Admin_Panel.py` both use **SHA-256** to hash passwords.

SHA-256 is a general-purpose cryptographic hash. It was designed to be **fast** — which is
exactly what you **don't** want for passwords. A modern GPU can compute **10 billion** SHA-256
hashes per second. That means an attacker who gets your `users.json` file can run a brute-force
attack and crack a typical password in **seconds to minutes**.

Your `users.json` currently stores hashes like:
```
"password_hash": "ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f"
```
That is the SHA-256 hash of `"password"`. Any attacker with a precomputed rainbow table already
knows this without even cracking it.

**bcrypt** solves all of this:
- It is **intentionally slow** (~100ms per hash by design).
- It automatically generates and embeds a random **salt**, so the same password produces a
  different hash every time — rainbow table attacks are useless.
- Its **cost factor** (rounds=12) can be increased as hardware gets faster.

---

## Files You Need to Change

| File | Change |
|------|--------|
| `requirements.txt` | Add `bcrypt==4.1.2` |
| `auth.py` | Full rewrite: replace hashlib with bcrypt |
| `pages/5_Admin_Panel.py` | Replace `hashlib.sha256` with bcrypt |
| `users.json` | Migrate existing SHA-256 hashes to bcrypt |
| *(new)* `migrate_passwords.py` | One-time migration script |

---

## Step 1.1 — Install bcrypt

Run this in your terminal from the project root:

```bash
cd ~/ops-copilot_gemini

# Activate your virtual environment first
source venv/bin/activate

# Install bcrypt
pip install bcrypt==4.1.2

# Verify it installed correctly
python3 -c "import bcrypt; print('bcrypt version:', bcrypt.__version__)"
```

Expected output:
```
bcrypt version: 4.1.2
```

---

## Step 1.2 — Update requirements.txt

Open `requirements.txt` and add this line under the `# ── Web Framework ──` section or at the
end. The full updated file should look like this:

**File: `requirements.txt`** (full content — replace entire file)

```
# LLM and AI
google-generativeai
anthropic
openai

# LangChain
langchain
langchain-community
langchain-anthropic
langchain-openai
langchain-google-genai

# Vector DB
chromadb
sentence-transformers

# Document Processing
pypdf
python-dotenv

# Web Framework
streamlit

# Evaluation
ragas
datasets

# Scheduling
apscheduler

# YAML support
pyyaml

# Security — bcrypt for password hashing (replaces hashlib SHA-256)
bcrypt==4.1.2
```

**Why pin to 4.1.2?** Pinning the version ensures that when you deploy to Azure, the exact same
version is installed. bcrypt 4.x changed the API slightly from 3.x, so pinning prevents
unexpected breakage.

---

## Step 1.3 — Full Replacement of auth.py

**Backup the existing file first:**
```bash
cp auth.py auth.py.sha256.backup
```

Now replace the **entire content** of `auth.py` with the following:

**File: `auth.py`** (full content — replace entire file)

```python
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

    Security notes:
    - We do NOT reveal whether the username or password was wrong.
      Both cases return None. This prevents username enumeration attacks.
    - We call verify_password() even for unknown users to maintain
      constant response time (prevents timing-based user enumeration).
    - The returned dict NEVER includes the password_hash.

    Args:
        username: The username submitted in the login form
        password: The plain-text password submitted in the login form

    Returns:
        dict with keys: username, display_name, customers, role
        OR None if credentials are invalid
    """
    try:
        if not username or not password:
            logger.warning("Login attempt with empty username or password")
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
            # Still call verify_password with a dummy hash to keep response
            # time consistent — prevents timing-based username enumeration.
            verify_password(password, "$2b$12$dummyhashfornon.existentuserXXXXXXXXXXXXXXXXXXXXXXXX")
            return None

        user = users[username]

        if not isinstance(user, dict):
            logger.error(f"Invalid user data structure for {username}")
            return None

        if 'password_hash' not in user:
            logger.error(f"Missing password_hash for user {username}")
            return None

        stored_hash = user['password_hash']

        # This is the key difference from the old SHA-256 code.
        # Old code: hashlib.sha256(password.encode()).hexdigest() == stored_hash
        # New code: bcrypt.checkpw() — handles salt, iterations, constant-time
        if not verify_password(password, stored_hash):
            logger.info(f"Failed login attempt for user: {username}")
            return None

        logger.info(f"Successful login for user: {username}")

        # Return safe user info — never include the password_hash itself.
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
```

---

## Step 1.4 — Full Replacement of pages/5_Admin_Panel.py

The Admin Panel was using `hashlib.sha256` directly to hash passwords when creating new users.
This MUST be replaced so that all user creation goes through `auth.py`'s `create_user()` function
which now uses bcrypt.

**File: `pages/5_Admin_Panel.py`** (full content — replace entire file)

```python
# pages/5_Admin_Panel.py
# Admin panel for user management
# SECURITY: Now uses auth.create_user() which hashes with bcrypt.
# The old version used hashlib.sha256 directly — that is now removed.

import streamlit as st
import json
from pathlib import Path
from auth_guard import require_authentication
from auth import create_user, delete_user, load_users

st.set_page_config(
    page_title='Admin Panel',
    page_icon='⚙️',
    layout='wide'
)

# Require authentication first — this stops unauthenticated access
user_info = require_authentication()

# Only admins can proceed past this point
if user_info.get('role') != 'admin':
    st.error('🔒 Admin access required')
    st.info('This page is only accessible to administrators.')
    st.stop()

st.title('⚙️ Admin Panel')
st.caption('User management and system administration')

# ── Load and display current users ────────────────────────────────────────────
try:
    users = load_users()
except Exception as e:
    st.error(f'Error loading users: {e}')
    st.stop()

st.subheader('Current Users')

try:
    import pandas as pd

    user_list = []
    for username, info in users.items():
        user_list.append({
            'Username': username,
            'Display Name': info.get('display_name', 'N/A'),
            'Role': info.get('role', 'N/A'),
            'Access': ', '.join(info.get('customers', ['General']))
        })

    df = pd.DataFrame(user_list)
    st.dataframe(df, use_container_width=True)
    st.metric('Total Users', len(users))

except Exception as e:
    st.error(f'Error displaying users: {e}')

# ── Add new user ──────────────────────────────────────────────────────────────
st.divider()
st.subheader('Add New User')

col1, col2 = st.columns(2)

with col1:
    with st.form('add_user'):
        new_username = st.text_input('Username', help='Lowercase, no spaces')
        new_password = st.text_input('Password', type='password')
        confirm_password = st.text_input('Confirm Password', type='password')
        new_display = st.text_input('Display Name', help='Full name with role, e.g. "Alice (SRE)"')
        new_role = st.selectbox('Role', ['sre', 'senior_sre', 'admin'])

        submit = st.form_submit_button('Add User', type='primary', use_container_width=True)

        if submit:
            if not new_username or not new_password or not new_display:
                st.error('❌ Please fill all required fields')
            elif new_password != confirm_password:
                st.error('❌ Passwords do not match')
            elif len(new_password) < 8:
                st.error('❌ Password must be at least 8 characters')
            elif ' ' in new_username:
                st.error('❌ Username cannot contain spaces')
            else:
                # create_user() in auth.py hashes the password with bcrypt
                # before saving. No SHA-256 anywhere.
                success = create_user(
                    username=new_username.lower().strip(),
                    password=new_password,
                    display_name=new_display,
                    role=new_role
                )
                if success:
                    st.success(f'✅ User {new_username} added successfully!')
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f'❌ Username "{new_username}" already exists')

with col2:
    st.info('''
    **Password Requirements:**
    - Minimum 8 characters
    - Mix of uppercase, lowercase, numbers, symbols recommended
    - Avoid common words or patterns

    **Role Types:**
    - **sre**: Regular SRE team member
    - **senior_sre**: Senior SRE with additional privileges
    - **admin**: Full system access including user management

    **Security Note:**
    Passwords are hashed with bcrypt (cost factor 12) before storage.
    The plain-text password is never saved anywhere.
    ''')

# ── Delete user ───────────────────────────────────────────────────────────────
st.divider()
st.subheader('Remove User')

col1, col2 = st.columns(2)

with col1:
    with st.form('delete_user'):
        deletable_users = [u for u in users.keys() if u != user_info['username']]

        if not deletable_users:
            st.info('No other users to delete.')
            st.form_submit_button('Delete User', disabled=True)
        else:
            delete_username = st.selectbox(
                'Select user to remove',
                options=deletable_users,
                help='Cannot delete your own account'
            )
            confirm = st.checkbox('I understand this action cannot be undone')
            delete_submit = st.form_submit_button('Delete User', type='secondary')

            if delete_submit:
                if not confirm:
                    st.error('❌ Please confirm deletion by checking the box')
                else:
                    success = delete_user(delete_username)
                    if success:
                        st.success(f'✅ User {delete_username} removed')
                        st.rerun()
                    else:
                        st.error(f'❌ Could not delete user {delete_username}')

with col2:
    st.warning('''
    **⚠️ Warning:**
    - Deleting a user is permanent
    - The user will lose access immediately
    - Their query history will remain in logs
    - You cannot delete your own account
    ''')

# ── System info ───────────────────────────────────────────────────────────────
st.divider()
st.subheader('System Information')

col1, col2, col3 = st.columns(3)

try:
    log_file = Path('query_log.json')
    if log_file.exists():
        with open(log_file) as f:
            log_data = json.load(f)
            total_queries = len(log_data.get('queries', []))
    else:
        total_queries = 0

    doc_count = 0
    for doc_dir in ['data/markdown', 'data/pdf', 'data/yaml']:
        if Path(doc_dir).exists():
            doc_count += sum(1 for _ in Path(doc_dir).rglob('*') if _.is_file())

    col1.metric('Total Users', len(users))
    col2.metric('Total Queries', total_queries)
    col3.metric('Documents Ingested', doc_count)

except Exception as e:
    st.warning(f'Could not load system stats: {e}')
```

**What changed in the Admin Panel:**
- **Removed** `import hashlib` — no more SHA-256 anywhere in this file
- **Replaced** the inline `hashlib.sha256(new_password.encode()).hexdigest()` hash with a call to
  `create_user()` from `auth.py`, which uses bcrypt internally
- **Added** password confirmation field (`confirm_password`) — catches typos before they lock a user out
- **Added** minimum password length validation (8 characters)
- **Added** username whitespace validation
- **Added** `delete_user()` import from `auth.py` instead of doing raw JSON manipulation inline

---

## Step 1.5 — Migrate Existing Users (One-Time Script)

Your current `users.json` has SHA-256 hashes. bcrypt cannot verify these — you must regenerate
them. Create this script, run it once, then delete it.

Create the file `migrate_passwords.py` in your project root:

```python
#!/usr/bin/env python3
# migrate_passwords.py
# ONE-TIME SCRIPT: Convert users.json from SHA-256 to bcrypt hashes.
# Run once, then DELETE this file (it contains plain-text passwords).

import bcrypt
import json
from datetime import datetime
from pathlib import Path

# ── EDIT THESE PASSWORDS ──────────────────────────────────────────────────────
# Set the new passwords for each user here.
# After running this script, share passwords with users via a secure channel
# (NOT email, NOT Slack — use a password manager or face-to-face).
NEW_PASSWORDS = {
    "alice":   "Alice@WSO2#2026!",
    "carol":   "Carol@WSO2#2026!",
    "admin":   "Admin@WSO2#VerySecure2026!!",
    "chalaka": "Chalaka@WSO2#2026!",
}
# ─────────────────────────────────────────────────────────────────────────────

USERS_FILE = "users.json"

print("=" * 60)
print("SRE Ops Copilot — Password Migration: SHA-256 → bcrypt")
print("=" * 60)
print()

# Load existing users.json
try:
    with open(USERS_FILE, "r") as f:
        data = json.load(f)
    users = data["users"]
    print(f"Loaded {len(users)} users from {USERS_FILE}")
except FileNotFoundError:
    print(f"ERROR: {USERS_FILE} not found!")
    exit(1)

# Create a timestamped backup before making any changes
backup_name = f"users.json.sha256.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
with open(backup_name, "w") as f:
    json.dump(data, f, indent=2)
print(f"Backup created: {backup_name}")
print()

# Generate new bcrypt hashes
print("Generating bcrypt hashes (about 1 second per user — this is intentional)...")
print("-" * 60)

new_users = {}
for username, user_data in users.items():
    if username in NEW_PASSWORDS:
        password = NEW_PASSWORDS[username]
    else:
        # User not in the list — generate a temporary password
        password = f"{username}@TempPW#2026"
        print(f"WARNING: No password defined for '{username}' — using temporary: {password}")

    # bcrypt.gensalt(rounds=12) + bcrypt.hashpw() takes ~100ms intentionally
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

    new_users[username] = {
        "password_hash": hashed.decode("utf-8"),
        "display_name":  user_data.get("display_name", username),
        "customers":     user_data.get("customers", ["ALL"]),
        "role":          user_data.get("role", "sre"),
    }

    # Verify the hash works correctly before saving
    assert bcrypt.checkpw(password.encode("utf-8"), hashed), f"Hash verification failed for {username}!"
    print(f"  {username:15s} → bcrypt hash generated and verified")

print("-" * 60)
print()

# Save updated users.json
data["users"] = new_users
with open(USERS_FILE, "w") as f:
    json.dump(data, f, indent=2)

print(f"users.json updated with bcrypt hashes.")
print()
print("=" * 60)
print("CREDENTIALS — Store in a password manager, NOT email/Slack:")
print("=" * 60)
for username, password in NEW_PASSWORDS.items():
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print()

print("NEXT STEPS:")
print("1. Test login for each user in the Streamlit app")
print("2. Distribute new passwords securely (password manager)")
print("3. DELETE this script: rm migrate_passwords.py")
print("4. DELETE the backup file once confirmed working")
```

**Run the migration:**
```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

# Edit the NEW_PASSWORDS dict in migrate_passwords.py with real passwords first
# Then run:
python3 migrate_passwords.py
```

**Expected output:**
```
============================================================
SRE Ops Copilot — Password Migration: SHA-256 → bcrypt
============================================================

Loaded 4 users from users.json
Backup created: users.json.sha256.backup.20260513_141230

Generating bcrypt hashes (about 1 second per user — this is intentional)...
------------------------------------------------------------
  alice           → bcrypt hash generated and verified
  carol           → bcrypt hash generated and verified
  admin           → bcrypt hash generated and verified
  chalaka         → bcrypt hash generated and verified
------------------------------------------------------------

users.json updated with bcrypt hashes.
```

**After confirming login works — delete the script:**
```bash
rm migrate_passwords.py
```

---

## Step 1.6 — Verify Everything Works

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

python3 - << 'EOF'
from auth import check_login, hash_password, verify_password

# Test 1: Correct password returns user info
result = check_login('admin', 'Admin@WSO2#VerySecure2026!!')
assert result is not None, "FAIL: Valid login returned None"
assert result['username'] == 'admin', "FAIL: Wrong username returned"
assert 'password_hash' not in result, "FAIL: password_hash leaked in result!"
print("PASS: Valid login works")

# Test 2: Wrong password returns None
result = check_login('admin', 'wrongpassword')
assert result is None, "FAIL: Invalid password accepted"
print("PASS: Invalid password rejected")

# Test 3: Non-existent user returns None
result = check_login('nobody', 'anything')
assert result is None, "FAIL: Non-existent user accepted"
print("PASS: Non-existent user rejected")

# Test 4: bcrypt hash format check
h = hash_password('test123')
assert h.startswith('$2b$12$'), f"FAIL: Unexpected hash format: {h[:10]}"
print("PASS: bcrypt hash format correct ($2b$12$...)")

# Test 5: verify_password works
assert verify_password('test123', h) == True, "FAIL: verify_password failed"
assert verify_password('wrong', h) == False, "FAIL: verify_password accepted wrong password"
print("PASS: verify_password works correctly")

print()
print("All tests passed. bcrypt authentication is working.")
EOF
```

---

## What Each Change Does in the Application Flow

```
User types password in login form
          ↓
app.py calls check_login(username, password)
          ↓
auth.py: load_users() reads users.json from disk
          ↓
auth.py: verify_password(typed_password, stored_bcrypt_hash)
          ↓
bcrypt.checkpw():
  1. Extracts 22-char salt from the stored hash
  2. Runs Blowfish cipher 4096 times with that salt + typed password
  3. Compares result to stored hash using constant-time comparison
          ↓
Returns True (match) or False (no match) — takes ~100ms regardless
          ↓
app.py sets session state and proceeds to main UI
```

The ~100ms delay is **intentional and desirable**. It makes brute-force attacks
10 billion times slower than SHA-256.
