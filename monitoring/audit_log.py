# audit_log.py
# ── Security Audit Logging ────────────────────────────────
# Records all security-relevant events to audit_log.json.
#
# This module is intentionally simple — it writes one JSON record
# per event, appending to a flat file. For production at scale,
# this should be replaced with a proper SIEM or logging service,
# but for a small team this file-based approach is sufficient.
#
# audit_log.json is listed in .gitignore (not committed to Git).
# On Azure, it should be on a persistent volume (not inside the container).

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = 'audit_log.json'

# Event type constants — use these instead of raw strings to avoid typos
LOGIN_SUCCESS    = 'LOGIN_SUCCESS'
LOGIN_FAILED     = 'LOGIN_FAILED'
LOGOUT           = 'LOGOUT'
SESSION_EXPIRED  = 'SESSION_EXPIRED'
USER_CREATED     = 'USER_CREATED'
USER_DELETED     = 'USER_DELETED'
QUERY_EXECUTED   = 'QUERY_EXECUTED'
RATE_LIMIT_HIT   = 'RATE_LIMIT_HIT'


def log_security_event(
    event_type: str,
    username: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None,
    success: bool = True,
):
    """
    Append one security event record to audit_log.json.

    The audit log is append-only within each run. On each call, we:
    1. Read the existing file (if it exists)
    2. Append the new record
    3. Write to a temp file first, then atomic rename — this prevents
       a partial write from corrupting the entire log file.

    Why atomic write? If the server crashes mid-write, a direct write
    would leave a half-written JSON file that crashes json.load().
    The temp-file-then-rename approach is atomic on most filesystems:
    either the full new file exists, or the old one — never a partial.

    Args:
        event_type: One of the constants above (LOGIN_SUCCESS, etc.)
        username:   The user involved in the event
        details:    Dict with extra context (e.g. {'method': 'password'})
        ip_address: Source IP if available (Streamlit doesn't expose this easily)
        success:    Whether the action succeeded (True for most events)
    """
    try:
        record = {
            'timestamp':  datetime.now().isoformat(),
            'event_type': event_type,
            'username':   username,
            'ip_address': ip_address,
            'success':    success,
            'details':    details,
        }

        # Load existing log (or start fresh)
        log_path = Path(AUDIT_LOG_FILE)
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                if 'events' not in log_data:
                    log_data = {'events': []}
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt audit log detected — starting fresh")
                log_data = {'events': []}
        else:
            log_data = {'events': []}

        # Append new record
        log_data['events'].append(record)

        # Atomic write: write to .tmp first, then rename
        temp_path = Path(f'{AUDIT_LOG_FILE}.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        # os.rename is atomic on POSIX filesystems (Linux, macOS)
        temp_path.replace(log_path)

        # Also emit to the Python logger (shows in journalctl / Docker logs)
        logger.info(
            f"AUDIT | {event_type} | user={username} | "
            f"ip={ip_address or 'unknown'} | success={success}"
        )

    except Exception as e:
        # NEVER let audit logging break the main application.
        # Log the failure but do not re-raise.
        logger.error(f"Failed to write audit log: {e}")


def get_failed_logins_last_n_minutes(minutes: int = 60) -> list:
    """
    Return a list of LOGIN_FAILED events from the last N minutes.

    Use this in an admin dashboard or monitoring script to detect
    brute-force attempts. If you see many failed logins for the same
    username in a short period, that user's account is under attack.

    Args:
        minutes: Time window to look back (default 60)

    Returns:
        list of event dicts for LOGIN_FAILED events in the window
    """
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []

        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        cutoff_ts = datetime.now().timestamp() - (minutes * 60)

        return [
            event for event in log_data.get('events', [])
            if event.get('event_type') == LOGIN_FAILED
            and datetime.fromisoformat(event['timestamp']).timestamp() > cutoff_ts
        ]

    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []


def get_user_audit_trail(username: str, limit: int = 50) -> list:
    """
    Return the most recent audit events for a specific user.

    Useful in the admin panel to show an admin what actions a user
    has taken (logins, logouts, queries).

    Args:
        username: User to get trail for
        limit:    Maximum events to return (most recent first)

    Returns:
        list of event dicts, sorted newest first
    """
    try:
        if not Path(AUDIT_LOG_FILE).exists():
            return []

        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)

        user_events = [
            e for e in log_data.get('events', [])
            if e.get('username') == username
        ]

        return sorted(user_events, key=lambda x: x['timestamp'], reverse=True)[:limit]

    except Exception as e:
        logger.error(f"Error reading audit trail for {username}: {e}")
        return []