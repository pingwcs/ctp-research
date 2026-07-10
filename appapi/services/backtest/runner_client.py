"""Subprocess orchestration for the quant runtime runner."""

from datetime import datetime
import json
import subprocess
from threading import Lock
from typing import Any

from fastapi import HTTPException, status
from loguru import logger

from appapi.core.config import settings


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


def invoke_runner(
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
    """JSON-line transport to one long-lived quant runtime worker process."""

    def __init__(self, process_factory=subprocess.Popen):
        self._process_factory = process_factory
        self._process = None
        self._lock = Lock()

    def invoke(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            output = self._send(command, payload or {})
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


_worker_transport: WorkerProcessTransport | None = None


def get_worker_transport() -> WorkerProcessTransport:
    global _worker_transport
    if _worker_transport is None:
        _worker_transport = WorkerProcessTransport()
    return _worker_transport


class RunnerJobClient:
    """Thin job facade over runner IPC, ready to swap subprocess for worker transport."""

    def __init__(self, invoke=None):
        if invoke is None:
            invoke = get_worker_transport().invoke
        self._invoke = invoke

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._invoke("submit", payload)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._invoke("status", {"job_id": job_id})

    def result(self, job_id: str) -> dict[str, Any]:
        return self._invoke("result", {"job_id": job_id})
