-- Initial API database schema. PostgreSQL runs this on first volume creation.
-- IF NOT EXISTS also keeps manual reapplication safe.

CREATE TABLE IF NOT EXISTS auth_users (
    email TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
