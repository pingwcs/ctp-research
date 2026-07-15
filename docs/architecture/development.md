# Development and Maintenance

## Local Configuration

Shared backend configuration is loaded in `global_config.py`. The main environment variables are:

| Variable | Purpose | Repository default |
| --- | --- | --- |
| `CTP_RESEARCH_PROJECT_ROOT` | Override the repository root used to resolve relative paths | repository root |
| `MARKET_DATA_DIR` | K-line parquet root | `data/output` |
| `MARKET_LOG_DIR` | API log directory | `appapi/logs` |
| `MARKET_CORS_ORIGINS` | Comma-separated browser origins | local Vite origins |
| `APPUI_DIST_DIR` | Built UI directory served by the API in a release | unset |
| `AUTH_DATABASE_DSN` | PostgreSQL connection for credentials and trading commands | local development DSN |
| `AUTH_TOKEN_SECRET` | HMAC secret for bearer tokens | insecure local-development value |
| `QUANT_RUNTIME_1MIN_DIR` | Canonical one-minute parquet directory | `data/output/1min` |
| `QUANT_RUNTIME_PYTHON` | Python executable used to start the quant runtime | current interpreter |

Production `runtime.env` is created outside the release directory by `scripts/production.py`. It contains generated secret values and must not be committed or copied into a release package.

## Running Services

Prepare a local environment once:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r appapi\requirements.txt
Set-Location appui
pnpm install
Set-Location ..
```

Start the developer API and UI without a container runtime:

```powershell
python scripts\dev.py
```

Use `-Target api`, `-Target ui` or `-Target pipeline` to start one component. The pipeline writes canonical market data directly:

```powershell
python scripts\dev.py pipeline
```

## Release Operations

`scripts/build_release.py` requires explicit paths to Python for Windows and PostgreSQL for Windows. It builds the UI, copies application code and runtime inputs, installs API dependencies into the packaged Python directory, and writes a secret-free manifest.

On the target host, `python\\python.exe scripts\\production.py start` creates the persistent runtime directory and starts PostgreSQL plus API. The script also provides `stop`, `restart`, `status`, `logs` and `backup`. The API serves the built UI directly at port 8000.

## Generated Artifacts

- `appui/src/api/generated/openapi.json` and `appui/src/api/generated/types.ts` are generated API artifacts. Regenerate them with `python scripts/generate_openapi.py`; do not hand-edit them.
- `data/input` contains raw local inputs. Canonical read models are written to `data/output/1min` and `data/output/5min`.
- `quant_runtime/runtime` contains runtime state such as the vn.py database and import manifest. Treat it as environment output, not application source.
- Frontend `dist` output, logs, caches, local environment files, secrets, release packages, and virtual environments are not architecture sources.

## Maintenance Rules

- Preserve package boundaries: HTTP mapping stays in `appapi`, strategy execution stays in `quant_runtime`, and broker-facing behavior stays in `trade_runtime` adapters.
- Change an HTTP contract through its schema and route first, regenerate the OpenAPI artifacts, then update the frontend client.
- Keep raw data immutable; regenerate canonical parquet outputs through the pipeline rather than patching read models manually.
- Treat live-trading changes as safety-sensitive: preserve idempotency, fencing, risk checks, auditability, and the no-blind-retry rule for unknown submissions.
- Update these architecture documents whenever a subsystem responsibility, dependency, persisted store, or primary flow changes.
