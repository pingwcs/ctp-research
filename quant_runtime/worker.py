"""Long-lived job worker for quant runtime backtests.

业务功能: 通过 stdin/stdout JSON-line 协议承载异步回测任务，供 appapi 长连接
复用。
算法要点: worker 内部用线程池执行回测，协议输出单独保留在原 stdout，
普通 print 被重定向到 stderr，避免破坏每行一个 JSON 响应的协议。
"""

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
    """业务功能: 记录一个异步回测任务的 payload、状态、结果和错误。"""

    job_id: str
    payload: dict[str, Any]
    status: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @property
    def error_detail(self) -> str | None:
        """业务功能: 给状态查询返回适合展示的失败原因。"""
        if not self.error:
            return None
        return str(self.error.get("detail") or "")


class InMemoryJobStore:
    """业务功能: 进程内任务表，适合当前单 worker 的短生命周期任务。

    算法要点: 所有读写都用同一把锁保护，避免提交线程、查询线程和执行线程
    同时更新 JobRecord 时出现状态撕裂。
    """

    def __init__(self) -> None:
        self._ids = count(1)
        self._records: dict[str, JobRecord] = {}
        self._lock = Lock()

    def submit(self, payload: dict[str, Any]) -> str:
        """业务功能: 创建 queued 任务并返回自增 job_id。"""
        with self._lock:
            job_id = f"job-{next(self._ids)}"
            self._records[job_id] = JobRecord(
                job_id=job_id,
                payload=payload,
                status="queued",
            )
            return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        """业务功能: 返回任务状态摘要。"""
        with self._lock:
            record = self._records[job_id]
            return {
                "job_id": record.job_id,
                "status": record.status,
                "error": record.error_detail,
            }

    def start(self, job_id: str) -> None:
        """业务功能: 将任务标记为 running。"""
        with self._lock:
            self._records[job_id].status = "running"

    def succeed(self, job_id: str, result: dict[str, Any]) -> None:
        """业务功能: 保存成功结果并标记任务完成。"""
        with self._lock:
            record = self._records[job_id]
            record.status = "succeeded"
            record.result = result

    def fail(self, job_id: str, status_code: int, detail: str) -> None:
        """业务功能: 保存失败状态码和错误详情。"""
        with self._lock:
            record = self._records[job_id]
            record.status = "failed"
            record.error = {"status_code": status_code, "detail": detail}

    def result(self, job_id: str) -> dict[str, Any]:
        """业务功能: 返回任务结果 envelope，未完成任务 result 为 None。"""
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
    """业务功能: 将 worker payload 转为 BacktestRequest 并执行回测。"""
    from quant_runtime.adapters.vnpy.backtester import run_backtest

    request = BacktestRequest.from_payload(payload)
    return run_backtest(request, minute_data_dir).to_jsonable()


class RuntimeJobWorker:
    """业务功能: 管理异步回测任务的提交、查询和后台执行。

    算法要点: 默认 max_workers=1 让 vn.py 数据库导入和回测串行执行，避免
    多任务同时删除/写入同一合约 bar 数据。
    """

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
        """业务功能: 提交任务并立即返回 queued/running 状态。"""
        job_id = self._store.submit(payload)
        self._executor.submit(self._run_job, job_id, payload)
        return self._store.status(job_id)

    def status(self, job_id: str) -> dict[str, Any]:
        """业务功能: 查询任务状态。"""
        return self._store.status(job_id)

    def result(self, job_id: str) -> dict[str, Any]:
        """业务功能: 查询任务结果或当前状态。"""
        return self._store.result(job_id)

    def _run_job(self, job_id: str, payload: dict[str, Any]) -> None:
        """算法要点: 捕获 RunnerError 为业务失败，其他异常统一转 500。"""
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
        """业务功能: 关闭 worker 线程池。"""
        self._executor.shutdown(wait=False, cancel_futures=True)


def handle_request(worker: RuntimeJobWorker, envelope: dict[str, Any]) -> dict[str, Any]:
    """业务功能: 处理一条 worker JSON-line 请求。"""
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
    """业务功能: 持续读取 JSON-line 请求并输出 JSON-line 响应。"""
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
    """业务功能: 定义 quant_runtime.worker 的启动参数。"""
    parser = argparse.ArgumentParser(prog="python -m quant_runtime.worker")
    parser.add_argument("--minute-data-dir", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """业务功能: worker 进程入口，初始化数据目录并启动 JSON-line 服务。"""
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
