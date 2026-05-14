#!/usr/bin/env python3
"""
migrate_json_to_pg.py
One-time script: copies existing JSON data into PostgreSQL.
Run this ONCE after the postgres container is running and healthy.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

# When running this script on your LOCAL machine, postgres is accessible at localhost:5432
# because docker-compose.yml exposes port 5432 on the host.
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://ops_user:ops_password@localhost:5432/ops_copilot'
)


def migrate_users(conn):
    print('Migrating users.json ...')
    users_file = Path('users.json')
    if not users_file.exists():
        print('  users.json not found — skipping')
        return 0

    with open(users_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    users = data.get('users', {})
    count = 0

    with conn.cursor() as cur:
        for username, info in users.items():
            cur.execute(
                """
                INSERT INTO users (username, password_hash, display_name, customers, role)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                (
                    username,
                    info.get('password_hash', ''),
                    info.get('display_name', username),
                    info.get('customers', ['ALL']),
                    info.get('role', 'sre'),
                )
            )
            count += 1

    conn.commit()
    print(f'  Done: {count} users inserted (duplicates skipped automatically)')
    return count


def migrate_audit_log(conn):
    print('Migrating audit_log.json ...')
    audit_file = Path('audit_log.json')
    if not audit_file.exists():
        print('  audit_log.json not found — skipping')
        return 0

    with open(audit_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    events = data.get('events', [])
    count = 0

    with conn.cursor() as cur:
        for event in events:
            try:
                ts = datetime.fromisoformat(event.get('timestamp', ''))
            except (ValueError, TypeError):
                ts = datetime.now()

            cur.execute(
                """
                INSERT INTO audit_log (timestamp, event_type, username, ip_address, success, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    ts,
                    event.get('event_type', 'UNKNOWN'),
                    event.get('username', 'unknown'),
                    event.get('ip_address'),
                    event.get('success', True),
                    psycopg2.extras.Json(event.get('details', {})),
                )
            )
            count += 1

    conn.commit()
    print(f'  Done: {count} audit events inserted')
    return count


def migrate_query_log(conn):
    print('Migrating query_log.json ...')
    query_file = Path('query_log.json')
    if not query_file.exists():
        print('  query_log.json not found — skipping')
        return 0

    with open(query_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    queries = data.get('queries', [])
    count = 0

    with conn.cursor() as cur:
        for q in queries:
            try:
                ts = datetime.fromisoformat(q.get('timestamp', ''))
            except (ValueError, TypeError):
                ts = datetime.now()

            # customer_scope in the JSON may be a list or a string
            scope = q.get('customer_scope', 'ALL')
            if isinstance(scope, list):
                scope = ','.join(scope)  # convert ['ALL'] to 'ALL'

            cur.execute(
                """
                INSERT INTO query_log
                    (timestamp, username, question, customer_scope,
                     answer_length, num_sources, latency_ms, success, error, top_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    ts,
                    q.get('username', 'unknown'),
                    q.get('question', ''),
                    scope,
                    q.get('answer_length', 0),
                    q.get('num_sources', 0),
                    q.get('latency_ms', 0),
                    q.get('success', True),
                    q.get('error'),
                    q.get('top_source'),
                )
            )
            count += 1

    conn.commit()
    print(f'  Done: {count} query records inserted')
    return count


if __name__ == '__main__':
    print(f'\nConnecting to: {DATABASE_URL}')
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print('Connected successfully.\n')
    except Exception as e:
        print(f'ERROR: Could not connect to database: {e}')
        print('Is the postgres container running? Try: docker compose ps')
        sys.exit(1)

    migrate_users(conn)
    migrate_audit_log(conn)
    migrate_query_log(conn)

    conn.close()
    print('\nMigration complete! Your JSON data is now in PostgreSQL.')
    print('You can verify with: docker compose exec postgres psql -U ops_user -d ops_copilot -c "SELECT COUNT(*) FROM users;"')