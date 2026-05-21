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

    Clears: authenticated flag, user_info, messages, activity timestamps,
    and the remember-me cookie so the user is not silently logged back in.
    """
    username = st.session_state.get('user_info', {}).get('username', 'unknown')

    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.messages = []

    # Clean up tracking timestamps
    for key in ['last_activity', 'session_start']:
        if key in st.session_state:
            del st.session_state[key]

    # Strip the session token from the URL so a refresh does not
    # re-authenticate. Import inside the function to avoid a circular
    # import at module load time.
    try:
        from auth.session_token import clear_session_token
        clear_session_token()
    except Exception as e:
        logger.warning(f"Could not clear session token on logout: {e}")

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