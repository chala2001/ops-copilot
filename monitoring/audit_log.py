# audit_log.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUDIT_LOG_FILE = 'audit_log.json'

# Event type constants
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
    Insert one security event into the audit_log table.
    """
    from db import get_db
    import psycopg2.extras
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log (timestamp, event_type, username, ip_address, success, details)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.now(),
                        event_type,
                        username,
                        ip_address,
                        success,
                        psycopg2.extras.Json(details),
                    )
                )

        logger.info(
            f"AUDIT | {event_type} | user={username} | "
            f"ip={ip_address or 'unknown'} | success={success}"
        )

    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")


def get_failed_logins_last_n_minutes(minutes: int = 60) -> list:
    """
    Return LOGIN_FAILED events from the last N minutes.
    """
    from db import get_db
    from datetime import timedelta
    try:
        cutoff = datetime.now() - timedelta(minutes=minutes)

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT timestamp, event_type, username, ip_address, success, details
                    FROM audit_log
                    WHERE event_type = %s AND timestamp > %s
                    ORDER BY timestamp DESC
                    """,
                    (LOGIN_FAILED, cutoff)
                )
                rows = cur.fetchall()

        return [
            {
                'timestamp':  row[0].isoformat(),
                'event_type': row[1],
                'username':   row[2],
                'ip_address': row[3],
                'success':    row[4],
                'details':    row[5] if isinstance(row[5], dict) else {},
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        return []


def get_user_audit_trail(username: str, limit: int = 50) -> list:
    """
    Return the most recent audit events for a specific user.
    """
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT timestamp, event_type, username, ip_address, success, details
                    FROM audit_log
                    WHERE username = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (username, limit)
                )
                rows = cur.fetchall()

        return [
            {
                'timestamp':  row[0].isoformat(),
                'event_type': row[1],
                'username':   row[2],
                'ip_address': row[3],
                'success':    row[4],
                'details':    row[5] if isinstance(row[5], dict) else {},
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error reading audit trail for {username}: {e}")
        return []