"""Subprocess orchestration for the quant runtime runner.

业务功能: 负责 appapi 与 quant_runtime 的进程边界通讯，包括一次性 CLI 调用
和长驻 worker 的 JSON-line 协议。
算法要点: 所有 runner 输出必须是 JSON 对象；stdout 承载协议响应，stderr
承载诊断日志，避免算法库的打印内容污染 HTTP 层解析。
"""

from datetime import datetime
import json
import subprocess
from threading import Lock
from typing import Any

from fastapi import HTTPException, status
from loguru import logger

from appapi.core.config import settings


def _cli_value(value: Any) -> str:
    """算法要点: 将 datetime 等 CLI 参数统一转换成 runner 可解析字符串。"""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _extend_payload_args(args: list[str], payload: dict[str, Any]) -> None:
    """业务功能: 将回测 payload 展开为 quant_runtime.runner 的命令行参数。"""
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
    """业务功能: 启动一次性 runner 进程并返回 JSON 结果。

    算法要点: 超时、启动失败、非法 JSON 和 runner 业务错误分别映射到
    504/503/502/runner 指定状态码，方便前端区分故障类型。
    """
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
    """JSON-line transport to one long-lived quant runtime worker process.

    业务功能: 复用一个 worker 进程承载异步回测任务，减少重复导入 VNPY 和
    初始化运行时的成本。
    算法要点: 通过锁串行化 stdin/stdout 读写，保证多线程 HTTP 请求不会把
    JSON-line 协议交叉写坏。
    """

    def __init__(self, process_factory=subprocess.Popen):
        self._process_factory = process_factory
        self._process = None
        self._lock = Lock()

    def invoke(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """业务功能: 向 worker 发送命令并把 worker 错误转换为 HTTPException。"""
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
        """算法要点: 一行请求对应一行响应，空行表示 worker 已退出。"""
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
        """业务功能: 懒启动或复用当前可用的 quant_runtime.worker 进程。"""
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
    """业务功能: 返回进程级单例 worker transport，复用后台运行时。"""
    global _worker_transport
    if _worker_transport is None:
        _worker_transport = WorkerProcessTransport()
    return _worker_transport


class RunnerJobClient:
    """Thin job facade over runner IPC, ready to swap subprocess for worker transport.

    业务功能: 为 service 层提供 submit/status/result 三个任务操作。
    算法要点: 构造时注入 invoke 函数，使测试可以替换真实进程通讯。
    """

    def __init__(self, invoke=None):
        if invoke is None:
            invoke = get_worker_transport().invoke
        self._invoke = invoke

    def submit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """业务功能: 提交异步回测任务。"""
        return self._invoke("submit", payload)

    def status(self, job_id: str) -> dict[str, Any]:
        """业务功能: 查询异步回测任务状态。"""
        return self._invoke("status", {"job_id": job_id})

    def result(self, job_id: str) -> dict[str, Any]:
        """业务功能: 查询异步回测任务结果。"""
        return self._invoke("result", {"job_id": job_id})
