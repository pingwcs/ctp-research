# Architecture Overview

## Purpose

FutureData CTP Research is a futures-market research platform that combines market-data preparation, browser-based K-line analysis, strategy backtesting, and an emerging live-trading foundation. This documentation describes the current repository for maintainers: which subsystem owns each responsibility, how data moves between them, and where deployment-specific boundaries begin.

## System Context

The React application in `appui` is the user-facing client. It calls the FastAPI service in `appapi` for authentication, K-line data, backtest metadata and execution, and manual trading commands.

Market data enters through `data_pipeline`, which normalizes raw contract CSV files into canonical one-minute and five-minute parquet datasets. `appapi` reads five-minute parquet files with DuckDB for K-line endpoints. `quant_runtime` reads one-minute parquet files, imports them into a vn.py database, and executes strategies either through its CLI or its long-lived JSON-lines worker.

The live-trading foundation separates durable command creation from broker execution. `appapi` authorizes and persists account-scoped commands, PostgreSQL stores trading records and fencing leases, Redis Streams provides the intended command/event transport, `trade_supervisor` owns single-runtime leases, and `trade_runtime` contains risk, order-state, idempotency, health, and CTP adapter boundaries.

## Subsystem Map

| Subsystem | Primary responsibility | Main collaborators |
| --- | --- | --- |
| `appui` | Browser UI, client state, typed HTTP calls, charts | `appapi` |
| `appapi` | HTTP contracts, authentication, market queries, orchestration, trading command persistence | parquet data, `quant_runtime`, PostgreSQL |
| `data_pipeline` | CSV cleaning, aggregation, quality reporting, canonical parquet output | `data/input`, `data/output`, optional InfluxDB |
| `quant_runtime` | Strategy catalog, market-data import, backtest execution, metrics | one-minute parquet, vn.py |
| `trade_runtime` | Per-account order processing and broker-facing boundaries | Redis Streams, CTP gateway, persistence ports |
| `trade_supervisor` | Per-account runtime leases and fencing tokens | PostgreSQL |
| `deploy` | Local live-trading infrastructure and runtime image definitions | Docker Compose, PostgreSQL, Redis |

## Runtime Status

The research path—data preparation, K-line browsing, and backtesting—is implemented and covered by repository tests. The live-trading code is an emerging foundation rather than a turnkey production service: core domain rules, persistence contracts, Redis adapters, leases, and CTP compatibility checks exist, but production operation still depends on account provisioning, secrets, a compatible Linux CTP runtime image, process supervision, and broker connectivity.

CTP credentials and native dependencies are environment-specific. Never store real account credentials in the repository; use the supplied example account contract and environment variables as references.

## Further Reading

- [Technology stack](tech-stack.md)
- [Component boundaries](components.md)
- [Data flows](data-flows.md)
- [Development and maintenance](development.md)
