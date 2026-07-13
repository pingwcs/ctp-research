# Technology Stack

## Languages and Runtimes

- Python 3.10 or newer is the documented minimum for backend, pipeline, quant, and trading modules.
- TypeScript 5.5 and React 18 are used by the browser application.
- Node.js 20.19 or newer and pnpm 10.33.0 are declared for frontend development. pnpm is pinned through `appui/package.json`.

Dependency files generally declare compatible minimum versions rather than a fully locked Python environment. The frontend lockfile, container image tags, and release metadata provide more exact reproducibility for their respective scopes.

## Frontend

The `appui` package is built with Vite 5 and React 18. Its main libraries are:

- React Router for client-side navigation;
- Redux Toolkit and React Redux for application state;
- Axios for HTTP access;
- Ant Design and Ant Design Icons for UI components;
- Lightweight Charts for K-line and equity visualization;
- Sass and Tailwind CSS/PostCSS for styling and responsive transformations.

TypeScript project references drive compilation. ESLint validates source rules, Prettier formats files, and Vite provides development, production build, preview, proxy, and bundle-analysis behavior.

## API and Services

`appapi` uses FastAPI and Uvicorn. Pydantic models supplied through FastAPI define HTTP request and response contracts. Loguru supplies application logging.

DuckDB reads local parquet datasets without loading entire files into an application-managed database. pandas supports tabular transformations, `psycopg` provides PostgreSQL access for authentication and live-trading persistence, and QuantStats is available for backtest analytics.

## Quant and Data

`data_pipeline` uses pandas and NumPy for cleaning and aggregation, PyArrow for parquet serialization, and the InfluxDB client for optional time-series writes.

`quant_runtime` uses pandas plus vn.py, `vnpy_ctastrategy`, and `vnpy_sqlite`. The runtime imports canonical one-minute parquet bars into the vn.py database before executing supported strategies. Strategy and metric metadata are exposed independently of the HTTP layer.

## Live-Trading Infrastructure

The live-trading foundation uses:

- PostgreSQL 16.9 in the Compose definition for tenant, account, command, order, event, outbox, and runtime-lease state;
- Redis 7.4.2 with append-only persistence for stream-based command and event transport;
- vn.py CTP integration inside the Linux trade-runtime image;
- Docker Compose for local PostgreSQL and Redis provisioning.

`deploy/trade-runtime/release-metadata.json` records the intended runtime artifact identity and native package versions. It is release metadata, not proof that a local machine has compatible CTP libraries or credentials.

## Developer Tooling

- pytest is the Python test runner used by the repository test suites.
- ESLint and Prettier validate and format the frontend.
- `scripts/generate_openapi.py` regenerates the checked-in OpenAPI document and TypeScript API types.
- `scripts/verify_ctp_runtime.py` performs offline runtime inspection and can prepare a protected SimNow connectivity probe.
- Docker and Docker Compose support the infrastructure and runtime-image workflows.
