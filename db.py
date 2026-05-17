# db.py
# Shared database connection helper.
# Usage in any module:
#     from db import get_db
#     with get_db() as conn:
#         with conn.cursor() as cur:
#             cur.execute("SELECT ...")

import psycopg2
import psycopg2.extras
import os
import logging
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read connection URL from the DATABASE_URL environment variable.
# Set in .env file and loaded by Docker via env_file: .env.
# Inside Docker containers, 'postgres' is the hostname (the service name in docker-compose).
# On your local machine, use 'localhost' instead.
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://ops_user:ops_password@postgres:5432/ops_copilot'
)


@contextmanager
def get_db():
    """
    Context manager that provides a PostgreSQL connection.

    On success:  auto-commits all changes made during the block.
    On error:    auto-rolls-back so no partial changes are saved.
    Always:      closes the connection when the block exits.

    Example:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users ...")
        # commit happens here automatically
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # Register adapters so JSONB columns return Python dicts automatically
        # instead of returning raw JSON strings.
        psycopg2.extras.register_default_json(conn)
        psycopg2.extras.register_default_jsonb(conn)
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()