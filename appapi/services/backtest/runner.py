"""Deep module for quant runtime calls."""

from __future__ import annotations

from datetime import datetime
from contextlib import contextmanager
import json
import subprocess
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Any, Callable, Protocol

from fastapi import HTTPException, status
from loguru import logger

from appapi.core.config import settings


class RuntimeAdapter(Protocol):
    def invoke(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke a quant runtime command."""


class BacktestConcurrencyGate:
    """Fail-fast capacity gate for locally executed backtests."""

    def __init__(self, max_active_jobs: int = 1) -> None:
        if max_active_jobs <= 0:
            raise ValueError("max_active_jobs must be positive")
        self._capacity = BoundedSemaphore(max_active_jobs)

    def try_acquire(self) -> bool:
        return self._capacity.acquire(blocking=False)

    def release(self) -> None:
        self._capacity.release()

    @contextmanager
    def acquire(self):
        if not self.try_acquire():
            raise RuntimeError("backtest capacity exhausted")
        try:
            yield
        finally:
            self.release()


_backtest_concurrency_gate = BacktestConcurrencyGate()


class BacktestJobCapacityRegistry:
    """Keep async capacity reserved until the worker reports a terminal state."""

    def __init__(self, gate: BacktestConcurrencyGate) -> None:
        self._gate = gate
        self._pending: set[object] = set()
        self._jobs: dict[str, object] = {}
        self._lock = Lock()

    def reserve(self) -> object:
        if not self._gate.try_acquire():
            raise RuntimeError("backtest capacity exhausted")
        token = object()
        with self._lock:
            self._pending.add(token)
        return token

    def bind(self, token: object, job_id: str) -> None:
        with self._lock:
            if token not in self._pending:
                return
            self._pending.remove(token)
            self._jobs[job_id] = token

    def release(self, token: object) -> None:
        with self._lock:
            if token not in self._pending:
                return
            self._pending.remove(token)
        self._gate.release()

    def release_job(self, job_id: str) -> None:
        with self._lock:
            token = self._jobs.pop(job_id, None)
        if token is not None:
            self._gate.release()

    def release_all(self) -> None:
        with self._lock:
            reservations = len(self._pending) + len(self._jobs)
            self._pending.clear()
            self._jobs.clear()
        for _ in range(reservations):
            self._gate.release()


_backtest_job_capacity = BacktestJobCapacityRegistry(_backtest_concurrency_gate)
_TERMINAL_JOB_STATUSES = {"succeeded", "failed"}
_JOB_STATUSES = {"queued", "running", *_TERMINAL_JOB_STATUSES}


class QuantRuntimeRunner:
    """One interface for runtime metadata, synchronous runs, and worker jobs."""

    def __init__(
        self,
        sync_adapter: RuntimeAdapter | None = None,
        worker_adapter: RuntimeAdapter | None = None,
        metadata_ttl_seconds: float = 30.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._sync_adapter = sync_adapter or SubprocessRuntimeAdapter()
        self._worker_adapter = worker_adapter or WorkerProcessTransport()
        self._metadata_ttl_seconds = metadata_ttl_seconds
        self._clock = clock
        self._cached_metadata: dict[str, Any] | None = None
        self._cached_metadata_at = 0.0

    def metadata(self) -> dict[str, Any]:
        now = self._clock()
        if (
            self._cached_metadata is not None
            and now - self._cached_metadata_at < self._metadata_ttl_seconds
        ):
            return self._cached_metadata

        self._cached_metadata = self._sync_adapter.invoke("metadata")
        self._cached_metadata_at = now
        return self._cached_metadata

    def list_symbols(self) -> list[str]:
        payload = self._sync_adapter.invoke("list-symbols")
        return [str(symbol) for symbol in payload.get("symbols", [])]

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_backtest("run", payload, self._sync_adapter)

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            reservation = _backtest_job_capacity.reserve()
        except RuntimeError as exc:
            raise _capacity_exhausted_http_error(exc) from exc

        try:
            output = self._invoke_worker("submit", payload)
            job_id = output.get("job_id")
            job_status = self._validated_job_status(output)
            if not isinstance(job_id, str):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="quant runtime worker returned an invalid job response",
                )
        except Exception:
            _backtest_job_capacity.release(reservation)
            raise

        if job_status in _TERMINAL_JOB_STATUSES:
            _backtest_job_capacity.release(reservation)
        else:
            _backtest_job_capacity.bind(reservation, job_id)
        return output

    def status(self, job_id: str) -> dict[str, Any]:
        try:
            output = self._invoke_worker("status", {"job_id": job_id})
            job_status = self._validated_job_status(output)
        except Exception:
            _backtest_job_capacity.release_job(job_id)
            raise
        if job_status in _TERMINAL_JOB_STATUSES:
            _backtest_job_capacity.release_job(job_id)
        return output

    def result(self, job_id: str) -> dict[str, Any]:
        try:
            output = self._invoke_worker("result", {"job_id": job_id})
            job_status = self._validated_job_status(output)
        except Exception:
            _backtest_job_capacity.release_job(job_id)
            raise
        if job_status in _TERMINAL_JOB_STATUSES:
            _backtest_job_capacity.release_job(job_id)
        return output

    def clear_metadata_cache(self) -> None:
        self._cached_metadata = None
        self._cached_metadata_at = 0.0

    def _invoke_worker(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        output = self._worker_adapter.invoke(command, payload)
        if not isinstance(output, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="quant runtime worker returned a non-object JSON payload",
            )
        error = output.get("error")
        if error:
            raise HTTPException(
                status_code=int(error.get("status_code") or 502)
                if isinstance(error, dict)
                else 502,
                detail=str(
                    error.get("detail")
                    if isinstance(error, dict)
                    else error
                    or "quant runtime worker failed",
                ),
            )
        return output

    @staticmethod
    def _validated_job_status(output: dict[str, Any]) -> str:
        job_status = output.get("status")
        if job_status not in _JOB_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="quant runtime worker returned an invalid job response",
            )
        return job_status

    def _invoke_backtest(
        self,
        command: str,
        payload: dict[str, Any],
        adapter: RuntimeAdapter,
    ) -> dict[str, Any]:
        try:
            with _backtest_concurrency_gate.acquire():
                output = adapter.invoke(command, payload)
        except RuntimeError as exc:
            if str(exc) != "backtest capacity exhausted":
                raise
            raise _capacity_exhausted_http_error(exc) from exc

        error = output.get("error")
        if error:
            raise HTTPException(
                status_code=int(error.get("status_code") or 502)
                if isinstance(error, dict)
                else 502,
                detail=str(
                    error.get("detail")
                    if isinstance(error, dict)
                    else error
                    or "quant runtime worker failed",
                ),
            )
        return output

    def shutdown(self) -> None:
        """Drop local reservations when this runner's worker is stopped or replaced."""
        _backtest_job_capacity.release_all()
        shutdown = getattr(self._worker_adapter, "shutdown", None)
        if callable(shutdown):
            shutdown()


def _capacity_exhausted_http_error(exc: RuntimeError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=str(exc),
    )


class SubprocessRuntimeAdapter:
    """One-shot subprocess adapter for quant_runtime.runner."""

    def invoke(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        args = [
            settings.quant_runtime_python,
            "-m",
            settings.quant_runtime_module,
            command,
            "--minute-data-dir",
            str(settings.quant_runtime_minute_data_dir),
        ]

        if payload is not None:
            _extend_payload_args(args, payload)

        try:
            completed = subprocess.run(
                args,
                check=False,
                capture_output=True,
                cwd=settings.project_root,
                text=True,
                timeout=settings.quant_runtime_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="quant runtime runner timed out",
            ) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"failed to start quant runtime runner: {exc}",
            ) from exc

        try:
            output = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            if completed.returncode != 0 and completed.stderr:
                logger.error("Quant runtime stderr: {}", completed.stderr)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=completed.stderr.strip(),
                ) from exc
            logger.error("Invalid quant runtime output: {}", completed.stdout)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="quant runtime runner returned invalid JSON",
            ) from exc

        if completed.returncode != 0 or "error" in output:
            error = output.get("error") or {}
            raise HTTPException(
                status_code=int(error.get("status_code") or 502),
                detail=str(
                    error.get("detail")
                    or completed.stderr
                    or "quant runtime failed",
                ),
            )
        return output


class WorkerProcessTransport:
    """JSON-line adapter to one long-lived quant runtime worker process."""

    def __init__(self, process_factory=subprocess.Popen) -> None:
        self._process_factory = process_factory
        self._process = None
        self._lock = Lock()

    def invoke(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            return self._send(command, payload or {})

    def shutdown(self) -> None:
        """Stop the worker so a replacement starts with no stale jobs."""
        with self._lock:
            process = self._process
            self._process = None
        if process is not None and process.poll() is None:
            process.terminate()

    def _send(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        process = self._ensure_process()
        request = json.dumps(
            {"command": command, "payload": payload},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            process.stdin.write(request + "\n")
            process.stdin.flush()
            line = process.stdout.readline()
        except (AttributeError, BrokenPipeError, OSError) as exc:
            self._process = None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"quant runtime worker unavailable: {exc}",
            ) from exc

        if not line:
            self._process = None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="quant runtime worker stopped",
            )
        try:
            output = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.error("Invalid quant runtime worker output: {}", line)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="quant runtime worker returned invalid JSON",
            ) from exc
        if not isinstance(output, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="quant runtime worker returned a non-object JSON payload",
            )
        return output

    def _ensure_process(self):
        if self._process is not None and self._process.poll() is None:
            return self._process

        try:
            self._process = self._process_factory(
                [
                    settings.quant_runtime_python,
                    "-m",
                    "quant_runtime.worker",
                    "--minute-data-dir",
                    str(settings.quant_runtime_minute_data_dir),
                ],
                cwd=settings.project_root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"failed to start quant runtime worker: {exc}",
            ) from exc
        return self._process


_quant_runtime_runner: QuantRuntimeRunner | None = None


def get_quant_runtime_runner() -> QuantRuntimeRunner:
    global _quant_runtime_runner
    if _quant_runtime_runner is None:
        _quant_runtime_runner = QuantRuntimeRunner()
    return _quant_runtime_runner


def clear_quant_runtime_runner() -> None:
    global _quant_runtime_runner
    if _quant_runtime_runner is not None:
        _quant_runtime_runner.shutdown()
    _quant_runtime_runner = None


def _cli_value(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _extend_payload_args(args: list[str], payload: dict[str, Any]) -> None:
    option_names = {
        "symbol": "--symbol",
        "strategy": "--strategy",
        "start_time": "--start-time",
        "end_time": "--end-time",
    }
    for key, option in option_names.items():
        value = payload.get(key)
        if value is not None and value != "":
            args.extend([option, _cli_value(value)])

    for metric in payload.get("metrics") or []:
        args.extend(["--metric", _cli_value(metric)])
