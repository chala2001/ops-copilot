# STEP 6 — Local Testing Checklist Before Azure Deployment

## Overview

Before deploying to Azure, validate every security change locally. This checklist covers
each step in order. Complete them all before moving to Azure — a mistake caught locally
costs minutes; one caught in production costs hours.

**Estimated time for full local validation: 45-60 minutes**

---

## Prerequisites

Make sure you have completed all previous steps:
- [ ] STEP1: bcrypt installed, auth.py replaced, Admin Panel updated, users migrated
- [ ] STEP2: session_manager.py created, app.py updated with timeout, auth_guard.py updated
- [ ] STEP3: .gitignore updated, config.py updated, .env permissions set
- [ ] STEP4: audit_log.py created, rate_limiter.py created, auth.py updated with audit+rate
- [ ] STEP5: .streamlit/config.toml created, Dockerfile and docker-compose.yml updated

---

## Phase 1 — Environment & Dependencies

### 1.1 — Fresh dependency install

```bash
cd ~/ops-copilot_gemini
source venv/bin/activate

# Ensure bcrypt is installed
pip install -r requirements.txt

# Verify bcrypt specifically
python3 -c "import bcrypt; print('bcrypt OK:', bcrypt.__version__)"
```
Expected: `bcrypt OK: 4.1.2`

### 1.2 — Config validation

```bash
python3 -c "
from config import GOOGLE_API_KEY, LLM_MODEL, CHROMA_PATH
print('API key loaded:', GOOGLE_API_KEY[:8] + '...')
print('LLM model:', LLM_MODEL)
print('ChromaDB path:', CHROMA_PATH)
print('config.py OK')
"
```
Expected: No SystemExit, prints key prefix starting with `AIzaSy`

### 1.3 — Module imports check

```bash
python3 -c "
import auth
import auth_guard
import session_manager
import audit_log
import rate_limiter
import logger
import config
import rag
print('All modules import successfully')
"
```
Expected: No ImportError or other exceptions

---

## Phase 2 — Authentication Tests

### 2.1 — bcrypt login works

```bash
python3 - << 'EOF'
from auth import check_login

# Replace these with the actual passwords you set in migrate_passwords.py
CREDENTIALS = {
    'admin':   'Admin@WSO2#VerySecure2026!!',
    'alice':   'Alice@WSO2#2026!',
    'carol':   'Carol@WSO2#2026!',
    'chalaka': 'Chalaka@WSO2#2026!',
}

passed = 0
failed = 0

for username, password in CREDENTIALS.items():
    result = check_login(username, password)
    if result and result['username'] == username:
        print(f"  PASS: {username} logs in correctly")
        passed += 1
    else:
        print(f"  FAIL: {username} login returned: {result}")
        failed += 1

print()
print(f"Results: {passed} passed, {failed} failed")
EOF
```
Expected: All users pass, 0 failed

### 2.2 — Wrong passwords rejected

```bash
python3 - << 'EOF'
from auth import check_login

tests = [
    ('admin',   'wrongpassword',        'Wrong password'),
    ('admin',   '',                     'Empty password'),
    ('',        'Admin@WSO2#2026!',     'Empty username'),
    ('nobody',  'somepassword',         'Non-existent user'),
    ('admin',   'Admin@wso2#2026!',     'Wrong case'),
]

for username, password, description in tests:
    result = check_login(username, password)
    if result is None:
        print(f"  PASS: {description} → correctly rejected")
    else:
        print(f"  FAIL: {description} → should have been rejected but returned {result}")
EOF
```
Expected: All 5 cases rejected (return None)

### 2.3 — password_hash not leaked

```bash
python3 - << 'EOF'
from auth import check_login

result = check_login('admin', 'Admin@WSO2#VerySecure2026!!')
assert result is not None, "Login failed"
assert 'password_hash' not in result, f"SECURITY FAIL: password_hash in result: {result}"
assert 'password' not in result, f"SECURITY FAIL: password in result: {result}"
print("PASS: password_hash not included in returned user_info dict")
EOF
```

---

## Phase 3 — Session Timeout Tests

### 3.1 — Session tracking initializes correctly

```bash
python3 - << 'EOF'
# We need to mock Streamlit session state for testing outside the app
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime

# Create a fake st.session_state dict
mock_session_state = {}

mock_st = MagicMock()
mock_st.session_state = mock_session_state
sys.modules['streamlit'] = mock_st

from session_manager import init_session_tracking, check_session_timeout

# Test init
init_session_tracking()
assert 'last_activity' in mock_session_state, "last_activity not set"
assert 'session_start' in mock_session_state, "session_start not set"
print("PASS: init_session_tracking() sets both timestamps")

# Test immediate check (should be valid)
valid, msg = check_session_timeout()
assert valid, f"Session should be valid immediately after init: {msg}"
assert msg == "", f"Message should be empty for valid session: {msg}"
print("PASS: Session valid immediately after initialization")

print("Session timeout unit tests passed (mocked Streamlit)")
EOF
```

### 3.2 — Manual UI test (requires running app)

1. Start the app: `streamlit run app.py`
2. Open: `http://localhost:8501`
3. Temporarily edit `session_manager.py`: change `SESSION_TIMEOUT_MINUTES = 60` to `SESSION_TIMEOUT_MINUTES = 1`
4. Log in with any valid account
5. Wait 65 seconds without interacting
6. Click anywhere in the app (a button, the chat input, anything)
7. You should see: "⏱️ Your session expired after 1 minutes of inactivity. Please log in again."
8. Click the re-login button — the login form should appear
9. Log in again — it should work normally
10. **Change SESSION_TIMEOUT_MINUTES back to 60**

---

## Phase 4 — Audit Log Tests

### 4.1 — Audit log writes correctly

```bash
python3 - << 'EOF'
import os
import json

# Clean up any existing test log
if os.path.exists('audit_log.json'):
    os.rename('audit_log.json', 'audit_log.test_backup.json')

from audit_log import log_security_event, get_failed_logins_last_n_minutes
from audit_log import LOGIN_SUCCESS, LOGIN_FAILED, USER_CREATED

log_security_event(LOGIN_SUCCESS, 'alice', {'method': 'password', 'role': 'senior_sre'})
log_security_event(LOGIN_FAILED, 'attacker', {'reason': 'wrong_password'}, success=False)
log_security_event(LOGIN_FAILED, 'attacker', {'reason': 'wrong_password'}, success=False)
log_security_event(USER_CREATED, 'admin', {'new_user': 'testuser', 'role': 'sre'})

# Verify file structure
with open('audit_log.json') as f:
    data = json.load(f)

assert 'events' in data, "audit_log.json missing 'events' key"
assert len(data['events']) == 4, f"Expected 4 events, got {len(data['events'])}"
print("PASS: audit_log.json has correct structure with 4 events")

# Verify failed login query
failed = get_failed_logins_last_n_minutes(60)
assert len(failed) == 2, f"Expected 2 failed logins, got {len(failed)}"
print("PASS: get_failed_logins_last_n_minutes returns correct count")

# Verify event types
event_types = [e['event_type'] for e in data['events']]
assert LOGIN_SUCCESS in event_types, "LOGIN_SUCCESS missing"
assert LOGIN_FAILED in event_types, "LOGIN_FAILED missing"
assert USER_CREATED in event_types, "USER_CREATED missing"
print("PASS: All event types present in log")

# Cleanup test file
os.remove('audit_log.json')
if os.path.exists('audit_log.test_backup.json'):
    os.rename('audit_log.test_backup.json', 'audit_log.json')

print()
print("All audit log tests passed")
EOF
```

### 4.2 — Audit log generated on login via the app

1. Run: `streamlit run app.py`
2. Log in with a valid account
3. Attempt to log in with a wrong password 2-3 times
4. Check: `cat audit_log.json | python3 -m json.tool | head -60`
5. You should see `LOGIN_SUCCESS` and `LOGIN_FAILED` events with timestamps

---

## Phase 5 — Rate Limiter Tests

### 5.1 — Query rate limiter

```bash
python3 - << 'EOF'
from rate_limiter import check_query_rate_limit

username = 'rate_test_user'

# Send 10 queries (should all be allowed)
for i in range(10):
    allowed, msg = check_query_rate_limit(username)
    assert allowed, f"Query {i+1} should be allowed: {msg}"

print("PASS: First 10 queries per minute allowed")

# 11th query should be blocked
allowed, msg = check_query_rate_limit(username)
assert not allowed, "11th query should be blocked"
assert 'rate limit' in msg.lower() or 'limit' in msg.lower(), f"Wrong message: {msg}"
print(f"PASS: 11th query blocked — message: '{msg[:60]}...'")

print()
print("Rate limiter tests passed")
EOF
```

### 5.2 — Login rate limiter

```bash
python3 - << 'EOF'
from rate_limiter import (
    check_login_rate_limit, record_failed_login, reset_login_attempts
)

username = 'login_rate_test'

# 5 failed attempts should be allowed (we check BEFORE recording, then record after)
for i in range(5):
    allowed, msg = check_login_rate_limit(username)
    assert allowed, f"Attempt {i+1} should be allowed: {msg}"
    record_failed_login(username)  # simulate failed login recording

print("PASS: 5 failed attempts recorded without lockout")

# 6th check should be blocked
allowed, msg = check_login_rate_limit(username)
assert not allowed, "6th attempt should be blocked"
print(f"PASS: Account locked after 5 failures — message: '{msg[:60]}...'")

# Reset and verify it's unlocked
reset_login_attempts(username)
allowed, msg = check_login_rate_limit(username)
assert allowed, "Should be allowed after reset"
print("PASS: Successful login resets the counter")

print()
print("Login rate limiter tests passed")
EOF
```

---

## Phase 6 — Docker Build Test

### 6.1 — Build the Docker image

```bash
cd ~/ops-copilot_gemini

# Build the image (this should succeed without errors)
docker build -t ops-copilot:test .

# Check the image was created
docker images | grep ops-copilot

# Verify the image runs as non-root
docker run --rm ops-copilot:test id
# Expected: uid=1000(appuser) gid=1000(appgroup) groups=1000(appgroup)
# NOT: uid=0(root)
```

### 6.2 — Run with Docker Compose

```bash
# Make sure .env has a valid GOOGLE_API_KEY
cat .env | grep GOOGLE_API_KEY

# Start the stack
docker-compose up -d

# Wait 30 seconds for the health check
sleep 35

# Check both containers are running and healthy
docker-compose ps
# Expected: ops-copilot-app is Up (healthy), ops-copilot-scheduler is Up

# Check app logs for startup errors
docker-compose logs app --tail=30

# Test the health endpoint
curl -f http://127.0.0.1:8501/_stcore/health && echo "HEALTHY"

# Stop when done
docker-compose down
```

---

## Phase 7 — Security Configuration Checks

### 7.1 — File permissions

```bash
# .env should be 600 (owner read/write only)
stat -c "%a %n" .env
# Expected: 600 .env

# users.json should be 600
stat -c "%a %n" users.json
# Expected: 600 users.json

# Private key (if using local HTTPS testing) should be 600
if [ -f certs/key.pem ]; then
    stat -c "%a %n" certs/key.pem
    # Expected: 600 certs/key.pem
fi
```

### 7.2 — .gitignore effectiveness

```bash
# Verify sensitive files would not be staged by git
git check-ignore -v .env
git check-ignore -v users.json
git check-ignore -v audit_log.json
git check-ignore -v query_log.json

# Each should output something like:
# .gitignore:10:.env  .env

# Verify nothing sensitive is currently tracked
git ls-files | grep -E "\.(env|key|pem)$"
# Expected: no output
```

### 7.3 — Verify users.json has bcrypt hashes

```bash
python3 - << 'EOF'
import json

with open('users.json') as f:
    data = json.load(f)

users = data['users']
all_ok = True

for username, user in users.items():
    h = user.get('password_hash', '')
    if h.startswith('$2b$') or h.startswith('$2a$'):
        print(f"  PASS: {username} has bcrypt hash")
    else:
        print(f"  FAIL: {username} has NON-BCRYPT hash: {h[:20]}...")
        all_ok = False

if all_ok:
    print()
    print("All users have bcrypt hashes")
else:
    print()
    print("FAIL: Some users still have old hashes. Re-run migrate_passwords.py")
EOF
```

---

## Phase 8 — Full Application Test (Manual UI)

Run the complete app and test all major flows:

```bash
streamlit run app.py
```

Open `http://localhost:8501` and do the following:

### 8.1 — Login form

- [ ] Login with wrong password → shows "Incorrect username or password." (not a specific error)
- [ ] Login with empty username → shows "Please enter both username and password."
- [ ] Login with valid credentials → redirects to main chat UI
- [ ] Sidebar shows "✓ [Display Name]" and "Sign out" button
- [ ] Session info expander appears in sidebar (shows "Session active: 0 min")

### 8.2 — Query rate limiting

- [ ] Ask 10 questions quickly (paste the same question repeatedly)
- [ ] 11th question → "Query rate limit" error message appears
- [ ] Wait 60 seconds, ask again → works normally

### 8.3 — Admin Panel (page 5)

- [ ] Log in as a non-admin user (e.g., alice or carol)
- [ ] Navigate to Admin Panel → shows "🔒 Admin access required"
- [ ] Log out and log in as admin
- [ ] Navigate to Admin Panel → shows user table
- [ ] Add a test user with a password under 8 characters → validation error
- [ ] Add a test user with mismatched passwords → validation error
- [ ] Add a valid test user → success, user appears in table
- [ ] Delete the test user → removed from table

### 8.4 — Dashboard pages (pages 2, 3, 4)

- [ ] Open any dashboard page URL directly (e.g., `/2_Evaluation_Dashboard`)
- [ ] Without logging in → shows "Access Denied" message
- [ ] After logging in → dashboard renders correctly

### 8.5 — Audit log check after testing

```bash
python3 -c "
import json
with open('audit_log.json') as f:
    events = json.load(f)['events']
print(f'Total events logged: {len(events)}')
for e in events[-10:]:
    print(f'  {e[\"timestamp\"][:19]} | {e[\"event_type\"]:20s} | {e[\"username\"]}')
"
```
You should see LOGIN_SUCCESS, LOGIN_FAILED events from your testing.

---

## Completion Checklist

Before moving to Azure deployment, confirm all of these:

- [ ] All Phase 1 environment checks pass
- [ ] All Phase 2 authentication tests pass (correct passwords accepted, wrong rejected)
- [ ] Phase 3 session timeout works (tested manually with 1-minute timeout)
- [ ] Phase 4 audit log creates events correctly
- [ ] Phase 5 rate limiters block correctly and reset correctly
- [ ] Phase 6 Docker build succeeds and container runs as non-root user
- [ ] Phase 7 file permissions and .gitignore are correct
- [ ] Phase 8 manual UI test passes all checkboxes
- [ ] users.json has bcrypt hashes (Phase 7.3 passes)
- [ ] No real API keys or passwords in any file that is git-tracked (`git status` shows nothing unexpected)

**If all pass → proceed to Azure deployment as described in the ENTERPRISE_DEPLOYMENT_GUIDE.md Section 4.**
