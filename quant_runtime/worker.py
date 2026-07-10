"""Long-lived job worker for quant runtime backtests."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from dataclasses import dataclass
from itertools import count
import json
from pathlib import Path
import sys
from threading import Lock
from typing import Any

from quant_runtime.contracts import BacktestRequest, RunnerError
from quant_runtime.settings import settings


@dataclass
class JobRecord:
    job_id: str
    payload: dict[str, Any]
    status: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @property
    def error_detail(self) -> str | None:
        if not self.error:
            return None
        return str(self.error.get("detail") or "")


class InMemoryJobStore:
    def __init__(self) -> None:
        self._ids = count(1)
        self._records: dict[str, JobRecord] = {}
        self._lock = Lock()

    def submit(self, payload: dict[str, Any]) -> str:
        with self._lock:
            job_id = f"job-{next(self._ids)}"
            self._records[job_id] = JobRecord(
                job_id=job_id,
                payload=payload,
                status="queued",
            )
            return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records[job_id]
            return {
                "job_id": record.job_id,
                "status": record.status,
                "error": record.error_detail,
            }

    def start(self, job_id: str) -> None:
        with self._lock:
            self._records[job_id].status = "running"

    def succeed(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            record = self._records[job_id]
            record.status = "succeeded"
            record.result = result

    def fail(self, job_id: str, status_code: int, detail: str) -> None:
        with self._lock:
            record = self._records[job_id]
            record.status = "failed"
            record.error = {"status_code": status_code, "detail": detail}

    def result(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            record = self._records[job_id]
            payload: dict[str, Any] = {
                "job_id": record.job_id,
                "status": record.status,
                "result": record.result,
            }
            if record.error is not None:
                payload["error"] = record.error
            return payload


def execute_backtest_payload(
    payload: dict[str, Any],
    minute_data_dir: Path,
) -> dict[str, Any]:
    from quant_runtime.adapters.vnpy.backtester import run_backtest

    request = BacktestRequest.from_payload(payload)
    return run_backtest(request, minute_data_dir).to_jsonable()


class RuntimeJobWorker:
    def __init__(
        self,
        minute_data_dir: Path = settings.minute_data_dir,
        execute=execute_backtest_payload,
        max_workers: int = 1,
    ) -> None:
        self._minute_data_dir = minute_data_dir
        self._execute = execute
        self._store = InMemoryJobStore()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = self._store.submit(payload)
        self._executor.submit(self._run_job, job_id, payload)
        return self._store.status(job_id)

    def status(self, job_id: str) -> dict[str, Any]:
        return self._store.status(job_id)

    def result(self, job_id: str) -> dict[str, Any]:
        return self._store.result(job_id)

    def _run_job(self, job_id: str, payload: dict[str, Any]) -> None:
        self._store.start(job_id)
        try:
            with redirect_stdout(sys.stderr):
                result = self._execute(payload, self._minute_data_dir)
        except RunnerError as exc:
            self._store.fail(job_id, exc.status_code, exc.detail)
        except Exception as exc:
            self._store.fail(job_id, 500, str(exc))
        else:
            self._store.succeed(job_id, result)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def handle_request(worker: RuntimeJobWorker, envelope: dict[str, Any]) -> dict[str, Any]:
    command = envelope.get("command")
    payload = envelope.get("payload") or {}
    if not isinstance(payload, dict):
        raise RunnerError(400, "worker payload must be an object")

    if command == "submit":
        return worker.submit(payload)
    if command == "status":
        return worker.status(str(payload.get("job_id") or ""))
    if command == "result":
        return worker.result(str(payload.get("job_id") or ""))
    raise RunnerError(400, f"unsupported worker command: {command}")


def serve(
    worker: RuntimeJobWorker,
    input_stream=sys.stdin,
    output_stream=sys.stdout,
) -> None:
    for line in input_stream:
        try:
            envelope = json.loads(line)
            if not isinstance(envelope, dict):
                raise RunnerError(400, "worker request must be a JSON object")
            response = handle_request(worker, envelope)
        except RunnerError as exc:
            response = exc.to_jsonable()
        except KeyError as exc:
            response = RunnerError(404, f"unknown job: {exc.args[0]}").to_jsonable()
        except Exception as exc:
            response = RunnerError(500, str(exc)).to_jsonable()
        print(
            json.dumps(response, ensure_ascii=False, separators=(",", ":")),
            file=output_stream,
            flush=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m quant_runtime.worker")
    parser.add_argument("--minute-data-dir", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    minute_data_dir = (
        Path(args.minute_data_dir).resolve()
        if args.minute_data_dir
        else settings.minute_data_dir
    )
    protocol_output = sys.stdout
    sys.stdout = sys.stderr
    worker = RuntimeJobWorker(minute_data_dir=minute_data_dir)
    try:
        serve(worker, output_stream=protocol_output)
    finally:
        worker.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
