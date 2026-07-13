# FutureData CTP Research

## Overview

FutureData CTP Research is a full-stack futures research platform for preparing market data, browsing K-line history, running strategy backtests, and developing a controlled CTP live-trading runtime.

The repository combines a FastAPI backend, React/Vite frontend, multiprocessing data pipeline, standalone vn.py-based quant runtime, and safety-oriented live-trading domain components.

## Capabilities

- Normalize raw futures CSV data into canonical one-minute and five-minute parquet datasets.
- Browse contract K-lines through a responsive web UI backed by DuckDB queries.
- Discover strategies and metrics, run synchronous or asynchronous backtests, and inspect equity and trade results.
- Register and authenticate users with PostgreSQL-backed credentials and signed bearer tokens.
- Accept tenant-scoped, idempotent manual-order commands into durable PostgreSQL records.
- Model risk checks, order lifecycles, Redis Stream delivery, runtime fencing, and CTP submission outcomes.

## Architecture

The main runtime path is:

```text
raw CSV -> data_pipeline -> canonical parquet
                                |-- appapi -> appui
                                `-- quant_runtime -> backtest results -> appapi -> appui

appui -> appapi -> PostgreSQL/outbox -> Redis Streams -> trade_runtime -> CTP
                      ^                                  |
                      `------- trade_supervisor ---------'
```

The research and backtest path is implemented. Live trading remains an emerging foundation that requires deployment integration, compatible Linux CTP dependencies, broker credentials, secrets, process supervision, callbacks, and reconciliation before production use.

See the [architecture overview](docs/architecture/README.md) for subsystem relationships and runtime status.

## Repository Map

| Path | Responsibility |
| --- | --- |
| `appui` | React UI, state, charts, and typed API clients |
| `appapi` | FastAPI routes, HTTP schemas, authentication, market queries, and orchestration |
| `data_pipeline` | CSV cleaning, aggregation, quality reporting, and parquet output |
| `quant_runtime` | Strategy/metric catalogs, vn.py import, backtest execution, and worker protocol |
| `trade_runtime` | Risk, orders, idempotency, health, Redis, and CTP adapter boundaries |
| `trade_supervisor` | Per-account runtime leases and fencing tokens |
| `deploy` | PostgreSQL/Redis Compose services and trade-runtime image files |
| `scripts` | OpenAPI generation and CTP runtime verification |
| `tests` | Cross-subsystem contract and behavior tests |
| `agent-docs` | Historical designs and implementation plans |
| `docs/architecture` | Current maintainer-oriented architecture reference |

## Quick Start

Prerequisites:

- Python 3.10+
- Node.js 20.19+
- pnpm 10.33.0, declared in `appui/package.json`

Start the backend from the repository root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r appapi\requirements.txt
python -m appapi.main
```

The API listens at `http://127.0.0.1:8000`; health is available at `http://127.0.0.1:8000/health`.

Start the frontend in another terminal:

```powershell
cd appui
pnpm install
pnpm dev
```

Vite listens at `http://127.0.0.1:5173` and proxies `/api` to the backend.

## Common Commands

```powershell
# Prepare market data
python data_pipeline\run.py --input-dir data/input --output-dir data/output

# Quant runtime dependencies
pip install -r quant_runtime\requirements.txt

# Inspect runtime metadata
python -m quant_runtime.runner metadata

# Import a contract into vn.py
python -m quant_runtime.runner import-data --payload-json '{"symbol":"RB0909","strategy":"ma_cross","metrics":[]}'

# Run a backtest directly
python -m quant_runtime.runner run --payload-json '{"symbol":"RB0909","strategy":"ma_cross","metrics":["total_return","max_drawdown"]}'

# Run all Python tests
.\venv\Scripts\python.exe -m pytest

# Frontend checks (from appui)
pnpm lint
pnpm build
```

## Configuration

Backend paths, CORS, authentication, and quant-runtime settings are controlled by environment variables defined in `global_config.py`. Single-host platform paths use `PLATFORM_ROOT`, which defaults to this repository and places data under `var/data`, market data under `var/data/market`, and state under `var/state`. Supply the PostgreSQL DSN through `PLATFORM_POSTGRES_DSN` outside source control; no database password belongs in tracked files. `PLATFORM_PRIVATE_NETWORK_ONLY` defaults to `true`. The frontend proxy reads `VITE_APPAPI_TARGET` and defaults to `http://127.0.0.1:8000`.

Local PostgreSQL and Redis services are defined in `deploy/compose.live-trading.yml`. Create required secret files locally and never commit database passwords, token secrets, or CTP account credentials.

## Private Platform Compose Stack

The platform stack runs only PostgreSQL and the API. It publishes both ports to loopback, so it is not a public-internet deployment. Copy the environment template, replace the local PostgreSQL password placeholders with the same value, and start the stack from the repository root:

```powershell
Copy-Item deploy\env\platform.env.example deploy\env\platform.env
# In deploy\env\platform.env, change PLATFORM_ENV_FILE to ./env/platform.env.
docker compose -f deploy/compose.platform.yml --env-file deploy/env/platform.env up -d
```

`deploy/env/platform.env` is intentionally untracked and supplies `PLATFORM_POSTGRES_DSN`. Do not place a real password in any tracked file. Tailscale is the only supported remote-access method: connect to the host over Tailscale, then access the loopback-bound services through an authenticated Tailscale/SSH tunnel. Do not expose the PostgreSQL or API ports publicly.

## Documentation

- [Architecture overview](docs/architecture/README.md)
- [Technology stack](docs/architecture/tech-stack.md)
- [Component boundaries](docs/architecture/components.md)
- [Data flows](docs/architecture/data-flows.md)
- [Development and maintenance](docs/architecture/development.md)
- [CTP account API contract](agent-docs/live-trading/ctp-account-api.md)

## Project Status

Market-data preparation, K-line browsing, authentication, and backtesting are implemented and tested. The live-trading modules establish safety and persistence contracts but are not yet a complete production trading service. Validate the pinned runtime image, native CTP libraries, SimNow connectivity, secrets handling, supervision, and recovery procedures before connecting any broker account.
