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