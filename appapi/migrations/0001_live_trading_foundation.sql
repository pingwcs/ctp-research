-- PostgreSQL schema for the first live-trading command path.
-- Applied by the deployment migration runner before appapi accepts live orders.

CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_members (
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    user_email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'trader', 'viewer')),
    PRIMARY KEY (tenant_id, user_email)
);

CREATE TABLE IF NOT EXISTS trading_accounts (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    broker_id TEXT NOT NULL,
    ctp_user_id TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('SIMNOW', 'LIVE')),
    desired_state TEXT NOT NULL DEFAULT 'STOPPED',
    runtime_state TEXT NOT NULL DEFAULT 'STOPPED',
    runtime_image_digest TEXT NOT NULL,
    settlement_auto_confirm_authorized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, broker_id, ctp_user_id, environment)
);

CREATE TABLE IF NOT EXISTS trade_commands (
    command_id TEXT PRIMARY KEY,
    order_intent_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    actor_email TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS order_intents (
    order_intent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    actor_email TEXT NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    direction TEXT NOT NULL,
    offset_policy TEXT NOT NULL,
    limit_price NUMERIC(20, 8) NOT NULL,
    volume INTEGER NOT NULL CHECK (volume > 0),
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS broker_orders (
    broker_order_id TEXT PRIMARY KEY,
    order_intent_id TEXT NOT NULL REFERENCES order_intents(order_intent_id),
    child_index INTEGER NOT NULL,
    offset TEXT NOT NULL,
    requested_volume INTEGER NOT NULL CHECK (requested_volume > 0),
    traded_volume INTEGER NOT NULL DEFAULT 0 CHECK (traded_volume >= 0),
    limit_price NUMERIC(20, 8) NOT NULL,
    status TEXT NOT NULL,
    order_ref TEXT,
    front_id INTEGER,
    session_id INTEGER,
    exchange_id TEXT,
    order_sys_id TEXT,
    UNIQUE (order_intent_id, child_index)
);

CREATE TABLE IF NOT EXISTS trade_event_journal (
    event_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    runtime_instance_id TEXT NOT NULL,
    fencing_token BIGINT NOT NULL,
    trading_day TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source_sequence TEXT,
    payload_json JSONB NOT NULL,
    payload_schema_version INTEGER NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (account_id, source, source_sequence)
);

CREATE TABLE IF NOT EXISTS trade_outbox (
    message_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES trading_accounts(id),
    message_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    dispatched_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS runtime_inbox (
    runtime_instance_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (runtime_instance_id, message_id)
);
