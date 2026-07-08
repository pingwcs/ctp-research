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
