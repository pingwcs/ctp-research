"""CLI runner used by appapi to call the quant runtime.

业务功能: 提供 list-symbols、metadata、import-data、run 四个命令，供 appapi
或本地命令行调用独立回测运行时。
算法要点: stdout 只输出最终 JSON 响应，运行过程中的打印被捕获后转到
stderr，保证调用方可以稳定解析协议结果。
"""

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing import Any

from quant_runtime.catalog import metadata
from quant_runtime.contracts import BacktestRequest, RunnerError
from quant_runtime.market_data import list_symbols
from quant_runtime.settings import settings


def _print_json(payload: dict[str, Any]) -> None:
    """业务功能: 以紧凑 JSON 输出 runner 协议响应。"""
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _payload_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """业务功能: 从 JSON 参数、JSON 文件或显式 CLI 参数构造 payload。

    算法要点: JSON 输入和命令行字段互斥优先；最终删除 None/空指标列表，
    让 BacktestRequest 保留运行时默认值。
    """
    if args.payload_json and args.payload_file:
        raise ValueError("use only one of --payload-json or --payload-file")

    if args.payload_json or args.payload_file:
        value = args.payload_json
        if args.payload_file:
            value = Path(args.payload_file).read_text(encoding="utf-8-sig")

        if not value:
            return {}
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("payload must be a JSON object")
        return parsed

    payload = {
        "symbol": args.symbol,
        "strategy": args.strategy,
        "start_time": args.start_time,
        "end_time": args.end_time,
        "metrics": args.metrics,
    }
    return {key: value for key, value in payload.items() if value not in (None, [])}


def _minute_data_dir(args: argparse.Namespace) -> Path:
    """业务功能: 解析本次 runner 命令使用的 1 分钟行情目录。"""
    value = args.minute_data_dir or args.input_dir
    return Path(value).resolve() if value else settings.minute_data_dir


def handle_command(args: argparse.Namespace) -> dict[str, Any]:
    """业务功能: 根据命令分派到元数据、行情导入或回测执行。

    算法要点: VNPY 相关模块延迟导入，避免 metadata/list-symbols 这类轻量
    命令承担策略引擎初始化成本。
    """
    minute_data_dir = _minute_data_dir(args)

    if args.command == "list-symbols":
        return {"symbols": list_symbols(minute_data_dir)}
    if args.command == "metadata":
        return metadata()
    if args.command == "import-data":
        from quant_runtime.adapters.vnpy.database import import_symbol_bars

        payload = _payload_from_args(args)
        request = BacktestRequest.from_payload(payload)
        count = import_symbol_bars(
            request.symbol,
            minute_data_dir,
            request.start_time,
            request.end_time,
        )
        return {"symbol": request.symbol, "bars": count}
    if args.command == "run":
        from quant_runtime.adapters.vnpy.backtester import run_backtest

        payload = _payload_from_args(args)
        request = BacktestRequest.from_payload(payload)
        return run_backtest(request, minute_data_dir).to_jsonable()

    raise RunnerError(400, f"unsupported runner command: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    """业务功能: 定义 quant_runtime.runner 的命令行协议。"""
    parser = argparse.ArgumentParser(prog="python -m quant_runtime.runner")
    parser.add_argument(
        "command",
        choices=["list-symbols", "metadata", "import-data", "run"],
    )
    parser.add_argument("--payload-json", default=None)
    parser.add_argument("--payload-file", default=None)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--start-time", default=None)
    parser.add_argument("--end-time", default=None)
    parser.add_argument("--metric", action="append", dest="metrics", default=[])
    parser.add_argument("--minute-data-dir", default=None)
    parser.add_argument("--input-dir", default=None, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    """业务功能: runner 进程入口，统一输出成功或失败的 JSON envelope。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    diagnostics = io.StringIO()
    try:
        with redirect_stdout(diagnostics):
            output = handle_command(args)
        _print_diagnostics(diagnostics)
        _print_json(output)
        return 0
    except RunnerError as exc:
        _print_diagnostics(diagnostics)
        _print_json(exc.to_jsonable())
        return 1
    except Exception as exc:
        _print_diagnostics(diagnostics)
        _print_json(RunnerError(500, str(exc)).to_jsonable())
        return 1


def _print_diagnostics(diagnostics: io.StringIO) -> None:
    """算法要点: 将被捕获的诊断输出转发到 stderr，避免污染 stdout JSON。"""
    value = diagnostics.getvalue()
    if value:
        print(value, file=sys.stderr, end="")


if __name__ == "__main__":
    raise SystemExit(main())
