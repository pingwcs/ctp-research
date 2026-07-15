"""Assemble a self-contained Windows release from explicit runtime inputs."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-root", type=Path)
    parser.add_argument("--postgres-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.python_root or not args.postgres_root:
        print("--python-root and --postgres-root are required", file=sys.stderr)
        return 2
    if not (args.python_root / "python.exe").is_file() or not (args.postgres_root / "bin" / "pg_ctl.exe").is_file():
        print("Runtime input is missing python.exe or bin\\pg_ctl.exe", file=sys.stderr)
        return 2
    output = args.output_root.resolve()
    if output == ROOT:
        print("--output-root must not be the repository root", file=sys.stderr)
        return 2
    if subprocess.run(["pnpm.cmd", "build"], cwd=ROOT / "appui").returncode:
        return 1
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ("appapi", "quant_runtime", "market_data", "trade_runtime", "trade_supervisor"):
        shutil.copytree(ROOT / name, output / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("global_config.py", "platform_config.py"):
        shutil.copy2(ROOT / name, output / name)
    shutil.copytree(ROOT / "appui" / "dist", output / "appui" / "dist")
    shutil.copytree(ROOT / "deploy" / "native", output / "deploy" / "native")
    shutil.copytree(ROOT / "deploy" / "postgres", output / "deploy" / "postgres")
    (output / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "production.py", output / "scripts" / "production.py")
    shutil.copytree(args.python_root, output / "python")
    shutil.copytree(args.postgres_root, output / "postgres")
    staged = output / "python" / "python.exe"
    if subprocess.run([str(staged), "-m", "pip", "install", "--no-cache-dir", "--target", str(output / "python" / "Lib" / "site-packages"), "-r", str(ROOT / "appapi" / "requirements.txt")]).returncode:
        return 1
    revision = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    (output / "release-manifest.json").write_text(json.dumps({"built_at": datetime.now(timezone.utc).isoformat(), "git_revision": revision, "python_source": str(args.python_root.resolve()), "postgres_source": str(args.postgres_root.resolve())}, indent=2), encoding="utf-8")
    print(f"Release assembled: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
