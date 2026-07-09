"""Subprocess orchestration for the quant runtime runner."""

from datetime import datetime
import json
import subprocess
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


class RunnerJobClient:
    """Thin job facade over runner IPC, ready to swap subprocess for worker transport."""

    def __init__(self, invoke=invoke_runner):
        self._invoke = invoke

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._invoke("submit", payload)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._invoke("status", {"job_id": job_id})

    def result(self, job_id: str) -> dict[str, Any]:
        return self._invoke("result", {"job_id": job_id})
