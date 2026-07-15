"""Native local development launcher."""

import argparse
import os
from pathlib import Path
import subprocess
import sys

from runtime_config import ConfigError, load_env


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default="all")
    args = parser.parse_args()
    if args.target not in {"all", "api", "ui", "pipeline"}:
        print(f"Unknown target: {args.target}", file=sys.stderr)
        return 2
    try:
        config = load_env(ROOT / "deploy" / "native" / "dev.env", production=False)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    python = ROOT / "venv" / "Scripts" / "python.exe"
    if not python.is_file():
        print(
            "Create the development environment first: python -m venv venv",
            file=sys.stderr,
        )
        return 2
    if args.target in {"all", "api"}:
        process = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "appapi.main:app",
                "--host",
                config["APPAPI_HOST"],
                "--port",
                config["APPAPI_PORT"],
                "--reload",
            ],
            cwd=ROOT,
            env={**os.environ, **config},
        )
        print(
            f"API started (PID {process.pid}): "
            f"http://{config['APPAPI_HOST']}:{config['APPAPI_PORT']}"
        )
    if args.target in {"all", "ui"}:
        process = subprocess.Popen(
            [
                "pnpm.cmd",
                "dev",
                "--host",
                config["UI_HOST"],
                "--port",
                config["UI_PORT"],
            ],
            cwd=ROOT / "appui",
        )
        print(
            f"UI started (PID {process.pid}): http://{config['UI_HOST']}:{config['UI_PORT']}"
        )
    if args.target == "pipeline":
        return subprocess.run(
            [
                str(python),
                "data_pipeline/run.py",
                "--input-dir",
                "data/input",
                "--output-dir",
                "data/output",
                "--market-root",
                "data/market",
                "--no-influx",
            ],
            cwd=ROOT,
        ).returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
