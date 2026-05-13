# STEP 2 — Session Timeout & Session Management

## Why This Is Needed

Your current system has **no session timeout**. Once a user logs in, they stay logged in
indefinitely — even if they:
- Close the browser tab and reopen it
- Leave their computer unlocked for hours
- Walk away from a shared workstation

In a corporate environment with sensitive customer deployment data, this is a real risk.
If Alice logs in at 9am and leaves her laptop open, anyone who sits at her desk can access
all customer data with zero authentication.

The fix is a `session_manager.py` module that:
1. Records when the user last did something (last activity timestamp)
2. Records when the session started (absolute start time)
3. Checks both on every page interaction
4. Forces logout if either threshold is exceeded

Two limits are enforced:
- **Inactivity timeout**: 60 minutes of no interaction → auto-logout
- **Max session duration**: 8 hours of total session → forced re-login even if active

---

## How Streamlit Sessions Work (Important Context)

Streamlit re-runs the **entire Python script** from top to bottom on every user interaction
(button click, form submit, typing in a chat box). This is different from traditional web apps.

`st.session_state` is a dictionary that persists across these re-runs **within the same browser
tab session**. It gets cleared when the user closes the tab or the server restarts.

So our session tracking works by:
- Storing `last_activity` and `session_start` timestamps in `st.session_state`
- On every re-run (every user interaction), checking if those timestamps have expired
- If expired, clearing `st.session_state.authenticated` and showing the login form

---

## Files You Need to Create/Change

| File | Change |
|------|--------|
| *(new)* `session_manager.py` | New module — all session logic lives here |
| `app.py` | Add 5 lines: import + init on login + check on every page load |
| `auth_guard.py` | Add session timeout check for dashboard pages |

---

## Step 2.1 — Create session_manager.py

Create a new file `session_manager.py` in the project root:

**File: `session_manager.py`** (new file — create from scratch)

```python
# session_manager.py
# ── Session Timeout Management ────────────────────────────
# Tracks user activity timestamps in Streamlit session state.
# Called on every page load to check if the session is still valid.

import streamlit as st
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────
# How long a user can be INACTIVE before being logged out.
# "Inactive" means no page interaction (no clicks, no form submits, no queries).
SESSION_TIMEOUT_MINUTES = 60

# Maximum total session length, even if the user stays active.
# After 8 hours, they must log in again regardless of activity.
# This limits damage from a stolen browser session.
SESSION_MAX_DURATION_HOURS = 8


def init_session_tracking():
    """
    Record the session start and initial last-activity timestamps.

    Call this ONCE when the user successfully logs in (in app.py,
    right after setting st.session_state.authenticated = True).

    How it works:
    - Sets st.session_state.last_activity = now
    - Sets st.session_state.session_start = now
    Both are datetime objects stored in Streamlit's session state dict.

    These values persist across page re-runs within the same browser
    session, but are lost if the server restarts or the browser tab closes.
    """
    now = datetime.now()
    st.session_state.last_activity = now
    st.session_state.session_start = now
    logger.info(f"Session tracking initialized at {now.isoformat()}")


def check_session_timeout() -> tuple:
    """
    Check whether the current session is still valid.

    Called on EVERY page load (every Streamlit re-run) for authenticated users.
    It does two checks:

    Check 1 — Inactivity timeout:
        If (now - last_activity) > SESSION_TIMEOUT_MINUTES → expired.
        This catches the "left the computer unlocked" scenario.
        last_activity is updated to 'now' on every VALID check (see below).

    Check 2 — Maximum duration:
        If (now - session_start) > SESSION_MAX_DURATION_HOURS → expired.
        This catches the "stayed logged in all day and night" scenario.
        Forces periodic re-authentication even for active users.

    IMPORTANT: last_activity is updated to 'now' only when the session is
    still VALID. If the session is expired, we do NOT update it — we let
    the calling code handle logout.

    Returns:
        (True, "")         — session is valid, continue normally
        (False, message)   — session expired, show message and log out
    """
    # If no tracking data exists, initialize it and return valid.
    # This handles the edge case where session_manager was not imported
    # at login time (e.g., during development/testing).
    if 'last_activity' not in st.session_state:
        init_session_tracking()
        return True, ""

    if 'session_start' not in st.session_state:
        st.session_state.session_start = datetime.now()

    now = datetime.now()

    # ── Check 1: Inactivity timeout ───────────────────────
    time_since_activity = now - st.session_state.last_activity

    if time_since_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        inactive_minutes = int(time_since_activity.total_seconds() / 60)
        message = (
            f'⏱️ Your session expired after {inactive_minutes} minutes of inactivity. '
            f'Please log in again.'
        )
        logger.warning(
            f"Session expired (inactivity): user was inactive for {inactive_minutes} minutes"
        )
        return False, message

    # ── Check 2: Maximum session duration ─────────────────
    session_duration = now - st.session_state.session_start

    if session_duration > timedelta(hours=SESSION_MAX_DURATION_HOURS):
        duration_hours = int(session_duration.total_seconds() / 3600)
        message = (
            f'⏱️ Session expired (maximum {SESSION_MAX_DURATION_HOURS}-hour duration reached). '
            f'Please log in again.'
        )
        logger.warning(
            f"Session expired (max duration): session was {duration_hours} hours long"
        )
        return False, message

    # ── Session is valid — update last_activity ────────────
    # This is the heartbeat: every page interaction resets the inactivity timer.
    # If a user clicks something every 59 minutes, they stay logged in.
    st.session_state.last_activity = now

    return True, ""


def logout_user():
    """
    Cleanly log out the user by clearing all session state.

    Call this when:
    - check_session_timeout() returns (False, message)
    - User clicks the "Sign out" button

    Clears: authenticated flag, user_info, messages, activity timestamps.
    """
    username = st.session_state.get('user_info', {}).get('username', 'unknown')

    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.messages = []

    # Clean up tracking timestamps
    for key in ['last_activity', 'session_start']:
        if key in st.session_state:
            del st.session_state[key]

    logger.info(f"User logged out: {username}")


def get_session_info() -> dict:
    """
    Return a dict with human-readable session timing information.
    Used to display session status in the sidebar (optional).

    Returns dict with keys:
        active (bool): Whether tracking data exists
        active_duration (str): How long the session has been running, e.g. "42 min"
        time_until_timeout (str): Time until inactivity logout, e.g. "18 min"
        inactivity_minutes (int): Minutes since last activity
    """
    if 'last_activity' not in st.session_state:
        return {'active': False, 'active_duration': 'N/A', 'time_until_timeout': 'N/A'}

    now = datetime.now()

    session_duration = now - st.session_state.session_start
    active_minutes = int(session_duration.total_seconds() / 60)

    time_since_activity = now - st.session_state.last_activity
    remaining = timedelta(minutes=SESSION_TIMEOUT_MINUTES) - time_since_activity
    remaining_minutes = max(0, int(remaining.total_seconds() / 60))

    return {
        'active': True,
        'active_duration': f'{active_minutes} min',
        'time_until_timeout': f'{remaining_minutes} min',
        'inactivity_minutes': int(time_since_activity.total_seconds() / 60),
    }


def display_session_status():
    """
    Show a collapsible session status panel in the sidebar.

    Call this in app.py's sidebar section if you want users to see
    when their session will expire. Optional but good for UX.

    Shows a warning when fewer than 10 minutes remain before auto-logout.
    """
    info = get_session_info()

    if info['active']:
        with st.sidebar:
            with st.expander('Session Info', expanded=False):
                st.caption(f"⏱️ Session active: {info['active_duration']}")
                st.caption(f"🔒 Auto-logout in: {info['time_until_timeout']}")

                if info['inactivity_minutes'] > SESSION_TIMEOUT_MINUTES - 10:
                    st.warning('⚠️ Session will expire soon due to inactivity')
```

---

## Step 2.2 — Update app.py (5 targeted changes)

You need to make **5 additions** to `app.py`. Find each location by the comment landmarks
shown and add the code.

### Change A — Add import at top of file

Find this block near the top of `app.py` (around line 6-9):

```python
# CURRENT CODE (do not delete):
import streamlit as st
from rag import ask, ask_stream, get_authorized_customers
import time
from logger import log_query
```

Add one import line after `from logger import log_query`:

```python
# CURRENT CODE (do not delete):
import streamlit as st
from rag import ask, ask_stream, get_authorized_customers
import time
from logger import log_query
from session_manager import check_session_timeout, init_session_tracking, logout_user
```

**Why here?** Imports at the top of the file run once when Streamlit first loads the script.
`session_manager` needs to be available both at login time (to call `init_session_tracking()`)
and on every authenticated page load (to call `check_session_timeout()`).

---

### Change B — Initialize session tracking on successful login

Find this block in the login section (around line 43-52):

```python
# CURRENT CODE:
        if submit:
            if not username or not password:
                st.error('Please enter both username and password.')
            else:
                user_info = check_login(username, password)
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user_info
                    st.rerun()
                else:
                    st.error('Incorrect username or password.')
```

Replace with:

```python
# UPDATED CODE — add init_session_tracking() call on successful login:
        if submit:
            if not username or not password:
                st.error('Please enter both username and password.')
            else:
                user_info = check_login(username, password)
                if user_info:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user_info
                    # Start session timer immediately after login.
                    # This records session_start and last_activity = now.
                    init_session_tracking()
                    st.rerun()
                else:
                    st.error('Incorrect username or password.')
```

**Why this placement?** `init_session_tracking()` must be called AFTER we confirm the user is
authenticated (i.e., after `check_login()` returns a non-None result) and BEFORE `st.rerun()`.
Calling it before the login check would set timestamps even for failed logins.

---

### Change C — Check session timeout on every authenticated page load

Find this line (around line 57-59):

```python
# CURRENT CODE:
# ── From here down, user is authenticated ────────────────
user_info = st.session_state.user_info
current_user = user_info['username']
```

Replace with:

```python
# UPDATED CODE — add session timeout check right after confirming authentication:
# ── From here down, user is authenticated ────────────────
user_info = st.session_state.user_info
current_user = user_info['username']

# Check session validity on every page load.
# check_session_timeout() returns (True, "") if valid, or (False, message) if expired.
# It also updates last_activity to now on every valid call — this is the heartbeat.
session_valid, timeout_message = check_session_timeout()

if not session_valid:
    # Session expired — show message and clean up state
    st.warning(timeout_message)
    logout_user()

    # Show re-login prompt
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.divider()
        if st.button('🔒 Click here to log in again', type='primary', use_container_width=True):
            st.rerun()
    st.stop()
```

**Why this placement?** This runs on EVERY page load for authenticated users because it comes
right after the `# ── From here down, user is authenticated ──` landmark. In Streamlit,
everything below `st.stop()` is skipped, so the expired session shows only the timeout message
and a re-login button.

---

### Change D — Add session status display in sidebar (optional but recommended)

Find the sidebar section (around line 82-96) where the sign-out button lives:

```python
# CURRENT CODE:
with st.sidebar:
    st.title('SRE Ops Copilot')
    st.caption('AI-powered deployment knowledge base')
    st.divider()

    # Show logged-in user
    st.success(f"✓ {user_info['display_name']}")
    if st.button('Sign out'):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.messages = []
        st.rerun()
```

Replace the sign-out button block with:

```python
# UPDATED CODE — use logout_user() and add session info:
with st.sidebar:
    st.title('SRE Ops Copilot')
    st.caption('AI-powered deployment knowledge base')
    st.divider()

    # Show logged-in user
    st.success(f"✓ {user_info['display_name']}")
    if st.button('Sign out'):
        logout_user()
        st.rerun()

    # Show session countdown (optional — helps users know when they'll be logged out)
    from session_manager import display_session_status
    display_session_status()
```

**Why use `logout_user()` instead of inline state clearing?**
The old code manually cleared 3 fields. `logout_user()` also clears the
session tracking timestamps (`last_activity`, `session_start`), so the next
login starts with a fresh timer. Centralizing this logic prevents bugs where
one place clears the auth fields but another forgets the timestamps.

---

## Step 2.3 — Update auth_guard.py (for dashboard pages)

The `auth_guard.py` file is used by the dashboard pages (`2_Evaluation_Dashboard.py`,
`3_Ingestion_Log.py`, `4_Usage_Dashboard.py`, `5_Admin_Panel.py`). It currently only checks
`st.session_state.authenticated` but doesn't enforce session timeout.

**File: `auth_guard.py`** (full content — replace entire file)

```python
# auth_guard.py
# Reusable authentication + session-timeout guard for dashboard pages.
# Call require_authentication() at the very top of every dashboard page.

import streamlit as st
from auth import check_login
from session_manager import check_session_timeout, init_session_tracking, logout_user


def require_authentication():
    """
    Enforce authentication and session timeout for a dashboard page.

    This function does three things:
    1. If not authenticated → show login form and stop rendering.
    2. If authenticated but session expired → show timeout message and stop.
    3. If authenticated and session valid → update last_activity and return user_info.

    Call at the very top of every multi-page dashboard file, BEFORE any
    other st.xxx calls (except st.set_page_config which must be first).

    Returns:
        dict: user_info dict (username, display_name, customers, role)
        Does NOT return if authentication fails — st.stop() is called.
    """

    # ── Initialize state if this is a first visit ──────────
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None

    # ── Show login form if not authenticated ───────────────
    if not st.session_state.authenticated:
        st.warning('🔒 Access Denied — Authentication Required')
        st.info('👉 Please log in via the main page (SRE Ops Copilot).')
        st.stop()

    # ── Check session timeout for authenticated users ──────
    # This runs on every page load for authenticated users on dashboard pages.
    session_valid, timeout_message = check_session_timeout()

    if not session_valid:
        st.warning(timeout_message)
        logout_user()
        st.info('👉 Please log in again via the main page.')
        st.stop()

    # ── Session is valid — show sign-out in sidebar ────────
    user_info = st.session_state.user_info

    with st.sidebar:
        st.success(f"✓ {user_info['display_name']}")
        if st.button('🚪 Sign out', use_container_width=True):
            logout_user()
            st.rerun()

    return user_info
```

**What changed in auth_guard.py:**
- Removed the inline login form. Dashboard pages redirect to the main page for login instead.
  This is cleaner and ensures login tracking is always initialized through one code path.
- Added `check_session_timeout()` call — dashboard pages now also enforce timeout.
- Used `logout_user()` instead of manually clearing session state.

---

## Step 2.4 — Test Session Timeout Locally

To test without waiting 60 minutes, temporarily change the timeout to 1 minute:

1. Open `session_manager.py`
2. Change `SESSION_TIMEOUT_MINUTES = 60` to `SESSION_TIMEOUT_MINUTES = 1`
3. Run the app: `streamlit run app.py`
4. Log in
5. Wait 62 seconds without clicking anything
6. Click anywhere in the app
7. You should see: "⏱️ Your session expired after 1 minutes of inactivity. Please log in again."
8. Click the "Click here to log in again" button — it should take you back to the login form
9. **Change SESSION_TIMEOUT_MINUTES back to 60** before committing

---

## Application Flow After This Change

```
Every page load for authenticated user:
          ↓
app.py (or auth_guard.py for dashboards) calls check_session_timeout()
          ↓
check_session_timeout() reads st.session_state.last_activity
                                                      ↓
                          (now - last_activity) > 60 min?
                                ↓YES                    ↓NO
                    Show timeout message      Update last_activity = now
                    Call logout_user()        Return (True, "")
                    Show re-login button      Continue rendering page
                    Call st.stop()
```

The 60-minute timer **resets on every page interaction**. If a user clicks a button at minute 59,
the timer resets to 0. This is the correct behavior — idle timeout, not absolute timer (the
absolute 8-hour timer handles the "active all day" case).
