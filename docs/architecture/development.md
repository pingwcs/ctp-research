# Development and Maintenance

## Local Configuration

Shared backend configuration is loaded in `global_config.py`. The main environment variables are:

| Variable | Purpose | Repository default |
| --- | --- | --- |
| `CTP_RESEARCH_PROJECT_ROOT` | Override the repository root used to resolve relative paths | repository root |
| `MARKET_DATA_DIR` | K-line parquet root | `data/output` |
| `MARKET_LOG_DIR` | API log directory | `appapi/logs` |
| `MARKET_CORS_ORIGINS` | Comma-separated browser origins | local Vite origins |
| `AUTH_DATABASE_DSN` | PostgreSQL connection for credentials and trading commands | local development DSN |
| `AUTH_TOKEN_SECRET` | HMAC secret for bearer tokens | insecure local-development value |
| `QUANT_RUNTIME_1MIN_DIR` | Canonical one-minute parquet directory | `data/output/1min` |
| `QUANT_RUNTIME_DATABASE` | vn.py database backend name | `sqlite` |
| `QUANT_RUNTIME_PYTHON` | Python executable used to start the quant runtime | current interpreter |
| `QUANT_RUNTIME_TIMEOUT_SECONDS` | one-shot runner timeout | `120` seconds |

Frontend development reads `VITE_APPAPI_TARGET` in `appui/vite.config.ts`; it defaults to `http://127.0.0.1:8000`. Real database passwords, CTP credentials, token secrets, and private fronts must stay outside version control.

## Running Services

From the repository root, start the API with:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r appapi\requirements.txt
python -m appapi.main
```

From `appui`, start the frontend with:

```powershell
pnpm install
pnpm dev
```

Prepare canonical market data with:

```powershell
python data_pipeline\run.py --input-dir data/input --output-dir data/output
```

Start local PostgreSQL and Redis after creating the untracked password secret required by the Compose file:

```powershell
docker compose -f deploy\compose.live-trading.yml up -d postgres redis
```

## Test Layout

Python tests live primarily under `tests`, with additional API tests under `appapi/tests`. They cover API services and contracts, pipeline output, quant-runtime domain and adapters, frontend source contracts, CTP compatibility checks, trade-runtime behavior, and supervisor leases.

Run the complete Python suite with the project environment:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Frontend checks are exposed through package scripts:

```powershell
cd appui
pnpm lint
pnpm build
```

## Generated Artifacts

- `appui/src/api/generated/openapi.json` and `appui/src/api/generated/types.ts` are generated API artifacts. Regenerate them with `python scripts/generate_openapi.py`; do not hand-edit them.
- `data/input` contains raw local inputs. Canonical read models are written to `data/output/1min` and `data/output/5min`.
- `quant_runtime/runtime` contains runtime state such as the vn.py database and import manifest. Treat it as environment output, not application source.
- Frontend `dist` output, logs, caches, local environment files, secrets, and virtual environments are not architecture sources.

## Maintenance Rules

- Preserve package boundaries: HTTP mapping stays in `appapi`, strategy execution stays in `quant_runtime`, and broker-facing behavior stays in `trade_runtime` adapters.
- Change an HTTP contract through its schema and route first, regenerate the OpenAPI artifacts, then update the frontend client.
- Keep raw data immutable; regenerate canonical parquet outputs through the pipeline rather than patching read models manually.
- Add tests at the owning boundary and run the full suite before integration.
- Treat live-trading changes as safety-sensitive: preserve idempotency, fencing, risk checks, auditability, and the no-blind-retry rule for unknown submissions.
- Update these architecture documents whenever a subsystem responsibility, dependency, persisted store, or primary flow changes.

