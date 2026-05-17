# logger.py - Query Logger with Complete Exception Handling


import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def log_query(
    username: str,
    question: str,
    customer_scope: list,
    answer: str,
    sources: list,
    latency_ms: int,
    success: bool = True,
    error: Optional[str] = None
):
    """
    Insert a query record into the query_log table.
    """
    from db import get_db
    try:
        if not username:
            username = 'unknown'
        if not question:
            question = ''
        if not isinstance(sources, list):
            sources = []

        top_source    = sources[0].get('source', 'Unknown') if sources else None
        answer_length = len(answer) if answer else 0

        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO query_log
                        (timestamp, username, question, customer_scope,
                         answer_length, num_sources, latency_ms, success, error, top_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        datetime.now(),
                        str(username),
                        str(question)[:500],
                        'ALL',
                        answer_length,
                        len(sources),
                        int(latency_ms) if latency_ms else 0,
                        bool(success),
                        str(error) if error else None,
                        top_source,
                    )
                )

    except Exception as e:
        logger.error(f"Unexpected error in log_query: {e}")
        # Fail silently — never disrupt the user experience for a logging failure


def load_log() -> List[Dict[str, Any]]:
    """
    Load all query records from the database.
    Returns the same list-of-dicts format as before, so Usage Dashboard needs no changes.
    """
    from db import get_db
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT timestamp, username, question, customer_scope,
                           answer_length, num_sources, latency_ms, success, error, top_source
                    FROM query_log
                    ORDER BY timestamp ASC
                    """
                )
                rows = cur.fetchall()

        return [
            {
                'timestamp':     row[0].isoformat(),
                'username':      row[1],
                'question':      row[2],
                'customer_scope': row[3],
                'answer_length': row[4],
                'num_sources':   row[5],
                'latency_ms':    row[6],
                'success':       row[7],
                'error':         row[8],
                'top_source':    row[9],
            }
            for row in rows
        ]

    except Exception as e:
        logger.error(f"Error loading query log: {e}")
        return []