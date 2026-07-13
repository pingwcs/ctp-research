# Data Flows

## Market-Data Ingestion

1. Operators place raw per-contract CSV files under `data/input` or pass another input directory to `data_pipeline/run.py`.
2. `data_pipeline.src.cleaner` parses and normalizes rows, reports anomalies, and produces a canonical one-minute frame.
3. `data_pipeline.src.aggregator` derives five-minute bars and daily-volume summaries.
4. Worker processes write one-minute contract files to `data/output/1min` and five-minute contract files to `data/output/5min`.
5. The pipeline writes its quality log and daily-volume summary under `data/output`. When configured, it also sends rows through the InfluxDB writer.

The parquet datasets are read models shared by later subsystems. Raw CSV inputs are not queried directly by the API or quant runtime.

## K-Line Query

1. `appui` requests symbols or a K-line window through `/api/market`.
2. `appapi.api.market` validates the HTTP request and delegates to the market-data service.
3. The service resolves the requested contract beneath `data/output/5min`; traversal outside that directory is rejected.
4. `appapi.services.kline_reader` uses DuckDB `read_parquet` queries to count, range-filter, and page normalized OHLCV rows.
5. The API returns typed JSON, Redux stores the result, and `KLineChart` renders it with Lightweight Charts.

## Backtesting

1. `appui` obtains symbol, strategy, and metric metadata from `/api/backtest` and submits a typed backtest request.
2. `appapi.services.backtest` converts the HTTP model into the quant-runtime payload; it does not run strategy code itself.
3. Synchronous requests start `python -m quant_runtime.runner`. Asynchronous requests use the long-lived `python -m quant_runtime.worker` JSON-lines process and poll by job identifier.
4. `quant_runtime` validates the request, loads canonical one-minute parquet data, imports bars into its vn.py database when needed, resolves the selected strategy, and executes the backtest.
5. The runtime computes the requested metrics and returns domain JSON. `appapi` maps that output into HTTP response DTOs, and `appui` renders metrics, equity, and trades.

## Authentication

1. Registration and login requests enter through `/api/auth`.
2. `AuthService` normalizes emails and hashes passwords with PBKDF2-SHA256. The first registered user receives the `admin` role; later users receive `user`.
3. `PostgresCredentialsStore` persists credentials in `auth_users`. Tests can inject the in-memory store.
4. Successful registration or login returns an HMAC-SHA256-signed bearer token containing the email and role.
5. Protected endpoints validate the signature, reload the user from the credential store, and apply role or tenant checks.

Tokens are signed but currently have no expiration claim. Production deployments must replace the documented local token secret and protect the database DSN.

## Live-Trading Commands

The repository implements the durable acceptance and core execution contracts, but not a complete production runtime deployment.

1. An authenticated user posts an order to `/api/trading/accounts/{account_id}/orders` with an `Idempotency-Key` header.
2. `TradingCommandService` checks tenant membership, hashes the payload, and rejects conflicting reuse of an idempotency key.
3. `PostgresTradingCommandStore` atomically creates the command, order intent, and `ORDER_SUBMIT_REQUESTED` outbox record.
4. The intended dispatcher publishes account-scoped work to Redis Streams. `trade_runtime.adapters.redis_streams` defines at-least-once consumption with an inbox guard for exactly-once effects.
5. A per-account runtime must hold the current fencing lease from `trade_supervisor`, evaluate risk, persist order-state transitions, and submit through the broker gateway boundary.
6. The CTP adapter maps accepted, rejected, and unknown submit outcomes. Unknown submissions are not blindly retried; later CTP callbacks or broker reconciliation must determine the final state.

Steps 1–3 and the domain/adapter contracts are present. Continuous outbox dispatch, container lifecycle supervision, live CTP callbacks, and operational reconciliation require deployment integration.
