# Task 3 Report: Bound Market Reads and Backtest Concurrency

## Delivered

- Added `appapi.services.market_query.MAX_QUERY_ROWS` (10,000) and
  `normalize_limit()`. Non-positive limits raise `ValueError("limit must be positive")`.
- Applied the normalizer at the market HTTP boundary and in the DuckDB-backed
  reader, so the route preserves `symbol`, `offset`, and `limit` while reads are
  capped at 10,000 rows.
- Added a thread-safe, non-blocking `BacktestConcurrencyGate` backed by a
  bounded semaphore. `QuantRuntimeRunner.run()` and `.submit()` acquire it and
  translate exhaustion to HTTP 429 with `backtest capacity exhausted`.
- Added focused unit, endpoint-function, and runner-integration regression
  coverage.

## TDD Evidence

### RED

Command:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_market_query.py tests/test_backtest_concurrency.py -q
```

Before production implementation, collection failed as expected because
`appapi.services.market_query` and `BacktestConcurrencyGate` did not exist.

### GREEN

Commands:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_market_query.py tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -c "import appapi.main; print('appapi.main import ok')"
& .\venv\Scripts\python.exe -m pytest -q
```

Final results: focused suite `7 passed`; import smoke printed
`appapi.main import ok`; full suite `18 passed`.

## Self-review

- The browser-facing limit applies both at HTTP handling and the actual
  DuckDB/Parquet reader; no data backend was changed.
- The backtest gate fails fast rather than blocking executor capacity, and
  preserves existing runtime error handling except for the new 429 mapping.
- The long-lived `quant_runtime.worker` already uses `ThreadPoolExecutor` with
  `max_workers=1`; this task deliberately does not modify that worker, CTP,
  PostgreSQL schema, or trading behavior.
- FastAPI `TestClient` could not be used in this environment because Starlette
  requires absent package `httpx2`; API regressions therefore call the existing
  endpoint functions directly and assert their FastAPI HTTP exceptions.

## Lifecycle concurrency follow-up

### Root cause

`QuantRuntimeRunner.submit()` held the concurrency gate only for the JSON-line
`submit` request. The worker then retained and ran the accepted job after that
method returned, so subsequent async submissions (and synchronous `run()`
calls) could enter concurrently.

### Fix

- Added a runner-side reservation registry. It reserves capacity before a
  worker submission, associates that reservation with the returned job ID, and
  releases it only after `status` or `result` reports `succeeded` or `failed`.
- Worker errors, malformed worker payloads, invalid submission responses,
  shutdown, and singleton-runner replacement clear outstanding reservations.
- The existing HTTP 429 boundary remains unchanged for exhausted capacity.
- Removed the unrelated `test_market_partitions.py` addition that was included
  in the prior Task 3 commit.

### TDD and verification

RED command:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_backtest_concurrency.py -q
```

Observed the new lifecycle regression fail as expected: a second async submit
was accepted while the first worker job remained queued/running.

GREEN / verification commands:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_market_query.py tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -m pytest -q
```

Final results: focused suite `8 passed`; full suite `18 passed`.

## Re-review reservation cleanup fix

### Root cause

`_invoke_worker()` cleared every outstanding reservation when any worker call
failed or returned malformed output. A `status` or `result` request for an
unrelated job could therefore release the capacity held by a queued/running
job.

### Fix

- Worker invocation now reports transport/error/malformed failures without
  clearing the global registry.
- `submit()` releases only its pending reservation when its own response is
  invalid or fails.
- `status()` and `result()` release only the reservation matching their
  requested job ID when that job's worker call fails or has an invalid status.
- All submit/status/result responses now accept only `queued`, `running`,
  `succeeded`, or `failed`; invalid statuses return HTTP 502.
- Shutdown and runner replacement still intentionally release all local
  reservations after stopping the owned worker.

### TDD and verification

RED command:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_backtest_concurrency.py -q
```

Observed `4 failed, 4 passed`: unrelated status/result errors freed the active
reservation, and malformed submit/status values were accepted.

GREEN / verification commands:

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -m pytest tests/test_market_query.py tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -c "import appapi.main; print('appapi.main import ok')"
& .\venv\Scripts\python.exe -m pytest -q
```

Final results: targeted concurrency suite `8 passed`; Task 3 focused suite
`12 passed`; import smoke printed `appapi.main import ok`; full suite `22 passed`.

## Final review-blocker fixes

### Root cause

- `status()` and `result()` trusted the worker's terminal `status` before
  confirming the response belonged to the requested job. A worker response for
  another (or missing/non-string) job ID could therefore release the active
  reservation for the requested job.
- The reservation registry was global, and `shutdown()` released every entry in
  that global registry. Shutting down one separately constructed runner could
  consequently free a job owned by another runner.

### Fix

- `status()` and `result()` now require a string response `job_id` exactly
  equal to the requested ID before validating a terminal state or releasing a
  reservation. Invalid identity responses return HTTP 502 and retain capacity.
- Registry reservations now carry an opaque runner-owner token; job lookup uses
  `(owner, job_id)` and shutdown releases only entries belonging to that
  runner. The existing global singleton API is unchanged.
- Added parameterized status/result regressions for mismatched, missing, and
  non-string worker job IDs, proving a second submit remains HTTP 429, plus a
  two-runner shutdown isolation regression.

### Fresh verification

```powershell
& .\venv\Scripts\python.exe -m pytest tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -m pytest tests/test_market_query.py tests/test_backtest_concurrency.py -q
& .\venv\Scripts\python.exe -c "import appapi.main; print('appapi.main import ok')"
& .\venv\Scripts\python.exe -m pytest -q
```

Results: targeted concurrency suite `15 passed`; Task 3 focused suite
`19 passed`; import smoke printed `appapi.main import ok`; full suite
`29 passed`.
