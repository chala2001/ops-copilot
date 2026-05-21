# auth/session_token.py
# ── Persistent login via signed URL query parameters ────
#
# Replaces the previous cookie-based approach. The cookie approach had three
# problems on this stack:
#   1. extra-streamlit-components performs cookie set/delete via an async
#      JavaScript message; st.rerun() fires before the browser writes the
#      cookie, so set / delete frequently miss.
#   2. The CookieManager runs in a Streamlit component iframe; Firefox
#      Private Browsing isolates iframe-set cookies from the main page jar,
#      so the cookie is never sent back at all.
#   3. The component returns None until its first render completes, causing
#      a visible flash of the login form on every refresh.
#
# st.query_params is built into Streamlit, synchronous, available on the
# very first line of the script, and not subject to any of the above. The
# token format and signing are unchanged from the cookie version, so the
# security model is identical.

import hmac
import hashlib
import logging
import os
import secrets
import time

import streamlit as st

logger = logging.getLogger(__name__)

# ── Token configuration ──────────────────────────────────
QUERY_PARAM = 's'          # the key used in the URL: ?s=...
TOKEN_LIFETIME_DAYS = 7

# Signing key — read from .env. Same SESSION_SECRET as before, so existing
# .env files continue to work unchanged.
_RAW_SECRET = os.getenv('SESSION_SECRET', '').strip()
if _RAW_SECRET:
    _SECRET_BYTES = _RAW_SECRET.encode('utf-8')
else:
    _SECRET_BYTES = secrets.token_bytes(32)
    logger.warning(
        'SESSION_SECRET is not set in .env — generated an ephemeral key. '
        'Persistent sessions will be invalidated whenever the container restarts. '
        'To fix, add SESSION_SECRET=<random hex string> to your .env file.'
    )


# ── Token signing helpers (unchanged from cookie version) ─
def _sign(payload: str) -> str:
    return hmac.new(_SECRET_BYTES, payload.encode('utf-8'), hashlib.sha256).hexdigest()


def _make_token(username: str, expiry_unix: int) -> str:
    payload = f'{username}|{expiry_unix}'
    return f'{payload}|{_sign(payload)}'


def _verify_token(token):
    """
    Return (username, expiry_unix) if the token is well-formed, unexpired,
    and signed correctly. Returns (None, None) otherwise.

    The expiry is exposed so callers can derive the original login time
    (expiry - TOKEN_LIFETIME_DAYS) and avoid resetting the 8-hour max-duration
    clock on every refresh.
    """
    if not token or not isinstance(token, str) or token.count('|') != 2:
        return None, None
    try:
        username, expiry_str, signature = token.split('|')
        expiry_unix = int(expiry_str)
    except (ValueError, AttributeError):
        return None, None

    if expiry_unix < int(time.time()):
        return None, None

    expected = _sign(f'{username}|{expiry_unix}')
    if not hmac.compare_digest(expected, signature):
        return None, None

    return username, expiry_unix


# ── Public API ────────────────────────────────────────────
def issue_session_token(username: str) -> None:
    """Write a fresh signed token to the URL after a successful login."""
    expiry_unix = int(time.time()) + TOKEN_LIFETIME_DAYS * 86400
    st.query_params[QUERY_PARAM] = _make_token(username, expiry_unix)
    logger.info(f'Session token issued for {username} (expires in {TOKEN_LIFETIME_DAYS} days)')


def clear_session_token() -> None:
    """Strip the token from the URL — used on logout."""
    if QUERY_PARAM in st.query_params:
        del st.query_params[QUERY_PARAM]
        logger.info('Session token cleared from URL')


def try_restore_session() -> bool:
    """
    If a valid token is in the URL, populate st.session_state and return True.

    Synchronous and instant — st.query_params is read directly from the request
    URL on every script run. No iframes, no async components, no first-frame
    flash of the login form.

    Side effect: when the user is already authenticated in session_state but
    the URL has lost the token (which happens whenever Streamlit's sidebar
    navigates between pages), this function re-writes the token into the URL.
    Without that, a refresh on a dashboard page would log the user out because
    session_state is wiped on refresh and there'd be no token to restore from.
    """
    from auth.auth import get_user_info
    from datetime import datetime

    if st.session_state.get('authenticated'):
        # Re-stamp the URL if Streamlit's page navigation dropped the token.
        if QUERY_PARAM not in st.query_params:
            username = (st.session_state.get('user_info') or {}).get('username')
            if username:
                issue_session_token(username)
        return True

    token = st.query_params.get(QUERY_PARAM)
    if not token:
        return False

    username, expiry_unix = _verify_token(token)
    if not username:
        # Token tampered with or expired — strip it so the user is not
        # stuck with a bad URL.
        clear_session_token()
        return False

    user_info = get_user_info(username)
    if not user_info:
        # User was deleted while their token was still valid — revoke it.
        clear_session_token()
        return False

    # Derive the original login timestamp from the token's expiry so the
    # 8-hour max-duration clock keeps counting from the real login time,
    # not from this refresh. Tokens always expire at (login_time + 7 days),
    # so subtracting the lifetime gives us the original login moment.
    original_login_unix = expiry_unix - TOKEN_LIFETIME_DAYS * 86400

    st.session_state.authenticated = True
    st.session_state.user_info = user_info
    st.session_state.session_start = datetime.fromtimestamp(original_login_unix)
    st.session_state.last_activity = datetime.now()
    logger.info(f'Session restored from URL token: {username}')
    return True
