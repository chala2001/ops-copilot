# auth/auth_guard.py
# Reusable authentication + session-timeout guard for dashboard pages.
# Call require_authentication() at the very top of every dashboard page.

import streamlit as st
from auth.auth import check_login
from auth.session_manager import check_session_timeout, init_session_tracking, logout_user
from auth.session_token import try_restore_session


def require_authentication():
    """
    Enforce authentication and session timeout for a dashboard page.

    Returns user_info dict if valid; calls st.stop() otherwise.
    """

    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None

    # Restore session from URL token if the browser was just refreshed —
    # otherwise users land on dashboards as "not logged in" after F5.
    try_restore_session()

    if not st.session_state.authenticated:
        st.warning('🔒 Access Denied — Authentication Required')
        st.info('👉 Please log in via the main page (SRE Ops Copilot).')
        st.stop()

    session_valid, timeout_message = check_session_timeout()

    if not session_valid:
        st.warning(timeout_message)
        logout_user()
        st.info('👉 Please log in again via the main page.')
        st.stop()

    user_info = st.session_state.user_info

    with st.sidebar:
        st.success(f"✓ {user_info['display_name']}")
        if st.button('🚪 Sign out', use_container_width=True):
            logout_user()
            st.rerun()

    return user_info
