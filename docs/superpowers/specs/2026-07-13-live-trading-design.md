# SimNow Multi-tenant Live Trading Design

## Goal

Add a production-shaped, multi-tenant CTP SimNow trading foundation for manual limit-order trading. The foundation makes account recovery, order correctness, risk decisions, and auditability more important than latency. Automated strategy execution is out of scope; a future strategy must submit the same internal order intent as a human user.

## Confirmed scope

- At most five tenants, five CTP accounts per tenant, and twenty-five concurrent accounts.
- Each CTP account belongs to exactly one tenant and runs in exactly one dedicated `trade_runtime` container.
- Ubuntu 24.04 LTS x86_64 is the host baseline. The `trade_runtime` image is immutable and referenced by digest.
- The first target is SimNow. The CTP stack is Python 3.12, vn.py 4.4.x, and `vnpy_ctp` 6.7.11.4, subject to an Ubuntu ABI smoke test.
- PostgreSQL is the business source of truth. Redis Streams is a delivery and fan-out mechanism, never the sole record of an order or trade.
- Only ordinary futures GFD limit orders, cancellation, open, close-today, and close-yesterday semantics are in scope. Market, FAK/FOK, conditional, combination, and option orders are excluded.
- A CTP account is exclusively traded by this platform. External activity blocks new opening orders until reconciliation.
- No automated liquidation. Risk events block opening, cancel active opening orders, and preserve manual closing.

## System boundaries

`appapi` owns HTTP, WebSocket, authentication, tenancy, command creation, and read models. It must not import vn.py or call CTP.

`trade_runtime` is a new top-level package. One instance owns one account's CTP session, settlement confirmation, pre-trade risk, serial command handling, broker-event journal, and recovery. It never trusts a client-supplied tenant identifier.

`trade_supervisor` owns account leases, fencing tokens, short-lived secret delivery, and the lifecycle of immutable runtime containers.

`market_runtime` is a separately deployed shared market-data process. It publishes timestamped snapshots; stale market data blocks opening orders but does not block safe cancellation and closing.

## Reliability model

An HTTP response that creates a command means only that PostgreSQL durably accepted the user intent. Redis acknowledgement, a CTP request return value, and a transport timeout are not broker acceptance.

`appapi` writes a `trade_commands` row and an outbox record in one PostgreSQL transaction. A dispatcher delivers the record to an account-partitioned Redis Stream. Runtime inbox de-duplication makes delivery at-least-once. Runtime events are append-only journal facts followed by idempotent projectors that build order, trade, position, and fund read models.

`SUBMIT_UNKNOWN` and `CANCEL_UNKNOWN` are mandatory states. A runtime never retries an uncertain CTP submit. It reconnects and queries the broker before selecting a terminal or active state.

## Core domain model

An `order_intent` records one human request. One intent can create several `broker_orders`, for example a `CLOSE_AUTO` request split between close-today and close-yesterday. The split and the position snapshot used to make it are immutable.

The broker order state machine is:

`CREATED -> RISK_CHECKING -> DISPATCH_PENDING -> SUBMITTING -> SUBMIT_UNKNOWN -> ACCEPTED -> PARTIALLY_FILLED -> FILLED`

Cancellation is:

`SUBMITTING|ACCEPTED|PARTIALLY_FILLED -> CANCEL_PENDING -> CANCEL_UNKNOWN -> CANCELLED`

Risk and broker rejection are terminal alternatives. Any active state can become `RECONCILE_REQUIRED`; no local timeout may silently make it terminal.

Client idempotency is unique on `(tenant_id, account_id, idempotency_key)`. Reusing a key with the same payload returns the original command; a different payload returns conflict.

## Risk and recovery

The runtime owns final synchronous risk checks in the same serial actor that sends CTP orders. Checks cover readiness, lease validity, session and trading day, rule version, instrument validity, tick, limits, fresh market data, price deviation, position, frozen close volume, estimated margin, active opening orders, and rate limits.

Risk rules are immutable, approved versions scoped from platform to tenant to account to instrument. A failure or stale critical state fails closed for opening. Cancellation is allowed. Closing remains possible after checks that prevent accidental reverse opening.

On startup or reconnect, the runtime confirms settlement under the account's pre-authorized daily confirmation, then queries broker orders, trades, positions, and funds. It accepts no new opening command until these facts are reconciled. Differences that cannot be resolved mechanically move the account to `DEGRADED` or `MANUAL_INTERVENTION_REQUIRED`.

## Security and operations

Sensitive CTP fields use envelope encryption: AES-256-GCM ciphertexts bind tenant, account, and field name as AAD; a host-held KEK wraps per-secret DEKs. API callers can replace secrets but never retrieve them. A supervisor-only secret broker exposes a short-lived read-only secret to the target container. Logs, errors, and audit payloads must redact secrets.

The first deployment is one Ubuntu trading host with automatic runtime-container restart and manual host recovery. PostgreSQL leases and monotonically increasing fencing tokens ensure an old process cannot consume new commands or send new orders after a replacement starts.

## Acceptance gates

Before SimNow is considered supported, the fixed Ubuntu image must import `vnpy_ctp`, resolve all shared libraries, create/release CTP APIs, authenticate, log in, confirm settlement, query funds/positions/orders/trades, subscribe market data, submit/cancel orders, survive forced runtime termination, and run across five trading days. Full test coverage includes state-machine property tests, fake-gateway fault injection, outbox/inbox idempotency, fencing, tenant isolation, and integration tests with PostgreSQL and Redis.
