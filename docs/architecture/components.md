# Component Boundaries

## `appui`

**Owns:** browser routing, authentication state, market and backtest state, responsive layout, K-line/equity rendering, typed HTTP clients, and user interaction.

**Depends on:** the `/api/auth`, `/api/market`, `/api/backtest`, and `/api/trading` contracts exposed by `appapi`.

**Does not own:** market-data normalization, strategy execution, credentials persistence, or broker connectivity.

## `appapi`

**Owns:** the FastAPI entry point, configuration, HTTP schemas, request validation, authentication, K-line queries, backtest orchestration and result mapping, and account-scoped trading command creation.

**Depends on:** five-minute parquet data and DuckDB for market queries; `quant_runtime` CLI/worker protocols for backtests; PostgreSQL for durable credentials and trading records when database configuration is supplied; selected in-memory adapters for development and tests.

**Does not own:** strategy simulation, canonical data preparation, or per-account broker sessions. Backtests are delegated to `quant_runtime`; trading commands stop at durable command/outbox creation.

## `data_pipeline`

**Owns:** discovering raw contract CSV files, cleaning and validating rows, producing quality logs, aggregating five-minute bars and daily volume, writing canonical parquet outputs, and optionally writing to InfluxDB.

**Depends on:** pandas, NumPy, PyArrow, local input/output directories, and optional InfluxDB configuration.

**Does not own:** HTTP serving, strategy execution, or live trading.

## `quant_runtime`

**Owns:** backtest request/domain contracts, strategy and metric catalogs, canonical one-minute market-data loading, vn.py database import, strategy execution, result metrics, CLI commands, and the long-lived job worker protocol.

**Depends on:** `data/output/1min`, pandas, vn.py, `vnpy_ctastrategy`, and `vnpy_sqlite`.

**Does not own:** HTTP schemas, UI result mapping, raw CSV cleanup, or broker account lifecycle.

## `trade_runtime`

**Owns:** order and idempotency domain rules, risk evaluation, serialized command handling, health/readiness state, Redis Stream delivery guards, persistence ports, and the boundary for a vn.py CTP gateway.

**Depends on:** caller-provided persistence and broker adapters. The Redis and CTP adapters are intentionally isolated from the domain and application layers.

**Does not own:** tenant authorization, HTTP command acceptance, account-runtime scheduling, or infrastructure provisioning. Some adapters are contract-level foundations and require deployment integration before production use.

## `trade_supervisor`

**Owns:** exclusive per-account runtime leases, monotonic fencing tokens, renewals, and release behavior. It includes in-memory and PostgreSQL-backed lease stores.

**Depends on:** a clock and, for durable production-style leases, PostgreSQL connectivity.

**Does not own:** order execution, CTP sessions, or process orchestration. The package currently supplies supervision primitives rather than a complete daemon.

## `deploy`

**Owns:** native Windows release configuration templates, the PostgreSQL initial schema, release assembly inputs, and runtime release metadata.

**Depends on:** a bundled PostgreSQL for Windows distribution, a bundled Python runtime, locally supplied market data, and secrets generated in the persistent runtime directory.

**Does not own:** application configuration defaults or secret values. `production.py` creates the local runtime configuration outside the release directory on first start.

## `scripts`

**Owns:** repository maintenance and compatibility entry points. `generate_openapi.py` produces API artifacts; `verify_ctp_runtime.py` checks native CTP runtime compatibility and optionally prepares a protected SimNow probe.

**Depends on:** the application packages or runtime environment being inspected.

**Does not own:** long-running application behavior.
