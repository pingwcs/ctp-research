# Live Trading Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the testable, provider-independent foundation for multi-tenant SimNow live trading before connecting any real CTP account.

**Architecture:** Add a standalone `trade_runtime` package with pure domain state machines and ports, then add PostgreSQL schemas and appapi commands around a transactional outbox. Keep CTP and Docker integrations behind adapters so unit and component tests can run without native CTP libraries.

**Tech Stack:** Python 3.12 target, FastAPI, Pydantic v2, PostgreSQL, Redis Streams, SQLAlchemy/Alembic, pytest, Hypothesis, vn.py 4.4.x, vnpy_ctp 6.7.11.4, Docker.

## Global Constraints

- The host target is Ubuntu 24.04 LTS x86_64; every runtime image is selected by immutable digest.
- PostgreSQL is the business source of truth; Redis Streams provides at-least-once delivery and fan-out only.
- One tenant owns one or more accounts; one account belongs to exactly one tenant and only one active runtime owns it.
- One account command actor is serial; uncertain CTP requests are never automatically retried.
- Monetary values use `Decimal` and database `NUMERIC`, never binary float.
- Opening fails closed; cancellation and validated closing remain available.

---

### Task 1: Restore the existing configuration test baseline

**Files:**
- Modify: `tests/test_global_config.py`

- [x] Replace `AUTH_USERS_FILE` in the fixture with `AUTH_DATABASE_DSN` and assert `config.auth_database_dsn`.
- [x] Run `venv\\Scripts\\python.exe -m pytest tests/test_global_config.py -q` and expect two passing tests.

### Task 2: Add pure trading primitives

**Files:**
- Create: `trade_runtime/domain/types.py`
- Create: `trade_runtime/domain/orders.py`
- Create: `tests/trade_runtime/test_orders.py`

- [x] Write failing tests for valid order transitions, terminal-state protection, and `CLOSE_AUTO` intent validation.
- [x] Run the focused test and observe import failure.
- [x] Implement enums, immutable dataclasses, and an explicit transition function with no CTP imports.
- [x] Run focused tests and then the full test suite.

### Task 3: Add deterministic idempotency and risk decisions

**Files:**
- Create: `trade_runtime/domain/idempotency.py`
- Create: `trade_runtime/domain/risk.py`
- Create: `tests/trade_runtime/test_idempotency.py`
- Create: `tests/trade_runtime/test_risk.py`

- [x] Write failing tests for payload hashing, same-key conflict detection, stale market-data opening rejection, and closing allowed while opening is blocked.
- [x] Implement only the pure domain functions needed by the tests.
- [x] Run focused and full Python tests.

### Task 4: Add application ports and a serial command handler

**Files:**
- Create: `trade_runtime/application/commands.py`
- Create: `trade_runtime/application/ports.py`
- Create: `tests/trade_runtime/test_commands.py`

- [x] Write failing tests against fake repositories and a fake gateway for risk rejection, successful submit dispatch, and no retry after uncertain submit.
- [x] Implement the handler with injected clock, repository, and gateway ports.
- [x] Run focused and full Python tests.

### Task 5: Add appapi contracts and transactional persistence migration

**Files:**
- Create: `appapi/schemas/trading/orders.py`
- Create: `appapi/services/trading/commands.py`
- Create: `appapi/api/trading.py`
- Modify: `appapi/main.py`
- Create: `appapi/migrations/0001_live_trading_foundation.sql`
- Create: `tests/appapi/services/test_trading_commands.py`

- [x] Write failing service tests for tenant-scoped idempotent order command creation.
- [x] Introduce a versioned PostgreSQL schema for tenants, accounts, commands, order intents, broker orders, event journal, outbox, and inbox.
- [x] Implement command persistence and expose only `POST /api/trading/accounts/{account_id}/orders` initially.
- [x] Run service tests, API tests, and the complete Python suite.

### Task 6: Add supervisor/runtime and Redis adapter seams

**Files:**
- Create: `trade_runtime/adapters/redis_streams.py`
- Create: `trade_supervisor/leases.py`
- Create: `tests/trade_runtime/test_redis_streams.py`
- Create: `tests/trade_supervisor/test_leases.py`

- [ ] Write failing tests for event de-duplication and fencing-token rejection.
- [ ] Implement provider-neutral interfaces plus Redis and PostgreSQL adapter implementations.
- [ ] Add Docker Compose development services and container health contracts without installing CTP.
- [ ] Run focused tests and the complete suite.

### Task 7: Add CTP image proof of compatibility and SimNow acceptance harness

**Files:**
- Create: `deploy/trade-runtime/Dockerfile`
- Create: `trade_runtime/adapters/vnpy_ctp/gateway.py`
- Create: `scripts/verify_ctp_runtime.py`
- Create: `tests/trade_runtime/test_vnpy_ctp_gateway.py`

- [ ] Write fake-gateway contract tests before importing vn.py.
- [ ] Build a pinned image and execute import/`ldd` checks.
- [ ] Run the credentialed SimNow harness only through an explicit protected environment.
- [ ] Record tested image digest and dependency versions in release metadata.
