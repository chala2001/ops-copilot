-- db/init.sql
-- Creates the three tables that replace users.json, audit_log.json, query_log.json.
-- Docker runs this file automatically on FIRST postgres container startup.
-- The IF NOT EXISTS clauses make it safe to re-run — nothing gets duplicated.

-- ── Users table ────────────────────────────────────────────
-- Replaces users.json
-- TEXT PRIMARY KEY: username must be unique — duplicate inserts are rejected
-- TEXT[]:  PostgreSQL array of strings, perfect for the customers list like ['ALL']
-- TIMESTAMPTZ: timestamp with timezone, always stored in UTC
CREATE TABLE IF NOT EXISTS users (
    username       TEXT PRIMARY KEY,
    password_hash  TEXT NOT NULL,
    display_name   TEXT NOT NULL DEFAULT '',
    customers      TEXT[] NOT NULL DEFAULT '{ALL}',
    role           TEXT NOT NULL DEFAULT 'sre',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Audit log table ────────────────────────────────────────
-- Replaces audit_log.json
-- BIGSERIAL: auto-incrementing ID (1, 2, 3, ...) — you never need to set this manually
-- JSONB: stores the details dict as structured JSON — faster than plain text for queries
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type  TEXT NOT NULL,
    username    TEXT NOT NULL,
    ip_address  TEXT,
    success     BOOLEAN NOT NULL DEFAULT TRUE,
    details     JSONB NOT NULL DEFAULT '{}'
);

-- Indexes make lookups fast.
-- Without these, finding "last 60 minutes of events" means scanning every single row.
-- With an index, PostgreSQL jumps directly to the matching rows.
CREATE INDEX IF NOT EXISTS idx_audit_timestamp  ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_username   ON audit_log(username);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);

-- ── Query log table ────────────────────────────────────────
-- Replaces query_log.json
CREATE TABLE IF NOT EXISTS query_log (
    id             BIGSERIAL PRIMARY KEY,
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    username       TEXT NOT NULL,
    question       TEXT,
    customer_scope TEXT NOT NULL DEFAULT 'ALL',
    answer_length  INTEGER NOT NULL DEFAULT 0,
    num_sources    INTEGER NOT NULL DEFAULT 0,
    latency_ms     INTEGER NOT NULL DEFAULT 0,
    success        BOOLEAN NOT NULL DEFAULT TRUE,
    error          TEXT,
    top_source     TEXT
);

CREATE INDEX IF NOT EXISTS idx_query_timestamp ON query_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_query_username  ON query_log(username);
