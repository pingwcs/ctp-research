# FutureData CTP Research

This repository contains a FastAPI backend (`appapi`) and a Vite React frontend (`appui`) for futures market data research, K-line browsing, and backtest result inspection.

## Prerequisites

- Python 3.10+
- Node.js 20.19+
- pnpm 10.33.0, declared by `appui/package.json`

## Backend

Run commands from the repository root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r appapi\requirements.txt
python -m appapi.main
```

The API starts on `http://127.0.0.1:8000` by default. A quick health check is available at `http://127.0.0.1:8000/health`.

## Runtime Boundaries

The project is split into four layers:

- `appui` owns UI state and typed HTTP client calls.
- `appapi` owns HTTP schemas, request validation, runner orchestration, and mapping quant domain results into HTTP DTOs.
- `data_pipeline` owns market-data normalization. Raw `data/input/*.csv` files are inputs only; canonical parquet read models are written under `data/output/1min` and `data/output/5min`.
- `quant_runtime` owns strategy metadata, metric metadata, vn.py adapter import, strategy execution, and domain backtest results.

`appapi` keeps the `/api/backtest/*` HTTP contract used by `appui`, but it does not contain strategy simulation code. It starts `quant_runtime.runner`, converts runner errors into HTTP errors, and maps runner domain JSON into API responses.

`quant_runtime` is the standalone quant backtesting runtime. Its current adapter is vn.py under `quant_runtime/adapters/vnpy`, and it imports canonical 1-minute parquet bars into the vn.py database before running strategies.

Install the quant runtime dependencies separately:

```powershell
pip install -r quant_runtime\requirements.txt
```

Import one symbol into the vn.py database:

```powershell
python -m quant_runtime.runner import-data --payload-json "{\"symbol\":\"RB0909\",\"strategy\":\"ma_cross\",\"metrics\":[]}"
```

Run one backtest directly:

```powershell
python -m quant_runtime.runner run --payload-json "{\"symbol\":\"RB0909\",\"strategy\":\"ma_cross\",\"metrics\":[\"total_return\",\"max_drawdown\"]}"
```

Run through the API after `python -m appapi.main` starts:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/backtest/run `
  -ContentType application/json `
  -Body '{"symbol":"RB0909","strategy":"ma_cross","metrics":["total_return"]}'
```

## Frontend

Run commands from `appui`:

```powershell
pnpm install
pnpm dev
```

Vite serves the app on `http://127.0.0.1:5173` and proxies `/api` to the backend target.

## Proxy Target

`appui/vite.config.ts` reads `VITE_APPAPI_TARGET` and defaults to `http://127.0.0.1:8000`.

Create `appui/.env.local` from `appui/.env.example` when the backend is running elsewhere:

```powershell
Copy-Item appui\.env.example appui\.env.local
```

Then edit `VITE_APPAPI_TARGET` in `appui/.env.local`.

## Common Commands

```powershell
# Frontend
cd appui
pnpm dev
pnpm build
pnpm lint
pnpm format
pnpm preview

# Backend
cd ..
python -m appapi.main
python scripts\lint_python.py appapi
```
