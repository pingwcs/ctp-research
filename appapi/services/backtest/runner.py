"""Deep module for quant runtime calls."""

from __future__ import annotations

from datetime import datetime
import json
import subprocess
from threading import Lock
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
        return self._sync_adapter.invoke("run", payload)

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_worker("submit", payload)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._invoke_worker("status", {"job_id": job_id})

    def result(self, job_id: str) -> dict[str, Any]:
        return self._invoke_worker("result", {"job_id": job_id})

    def clear_metadata_cache(self) -> None:
        self._cached_metadata = None
        self._cached_metadata_at = 0.0

    def _invoke_worker(self, command: str, payload: dict[str, Any]) -> dict[str, Any]:
        output = self._worker_adapter.invoke(command, payload)
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
