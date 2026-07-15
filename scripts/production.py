"""Lifecycle manager for a packaged FutureData Windows release."""

import argparse, os, subprocess, sys, time
from pathlib import Path
from urllib.request import urlopen
from runtime_config import ConfigError, load_env


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("start", "stop", "restart", "status", "logs", "backup")
    )
    parser.add_argument(
        "--release-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()
    release = args.release_root.resolve()
    runtime = (args.runtime_root or release.parent / "runtime").resolve()
    pg = release / "postgres" / "bin"
    ctl = pg / "pg_ctl.exe"
    if not ctl.is_file():
        print(f"Packaged PostgreSQL is incomplete: missing {ctl}", file=sys.stderr)
        return 2
    config = release / "deploy" / "env" / "prod.env"
    try:
        env = load_env(config, production=True)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    runtime = (args.runtime_root or Path(env["RUNTIME_ROOT"])).resolve()
    data, logs, config, pid = (
        runtime / "postgres" / "data",
        runtime / "logs",
        config,
        runtime / "api.pid",
    )

    def run(*command: str, **kwargs):
        return subprocess.run(command, check=False, **kwargs)

    def stop():
        if pid.exists():
            try:
                os.kill(int(pid.read_text()), 15)
            except OSError:
                pass
            pid.unlink(missing_ok=True)
        if data.exists():
            run(str(ctl), "-D", str(data), "stop", "-m", "fast")

    if args.command == "stop":
        stop()
        print("FutureData production platform stopped.")
        return 0
    if args.command == "restart":
        stop()
        args.command = "start"
    if args.command == "status":
        print("API process: running" if pid.exists() else "API process: stopped")
        return run(
            str(pg / "pg_isready.exe"),
            "-h",
            env["POSTGRES_HOST"],
            "-p",
            env["POSTGRES_PORT"],
            "-U",
            "futuredata",
        ).returncode
    if args.command == "logs":
        files = [
            p
            for p in (
                logs / "appapi.out.log",
                logs / "appapi.err.log",
                logs / "postgres.log",
            )
            if p.exists()
        ]
        if not files:
            print("No logs are available", file=sys.stderr)
            return 2
        for file in files:
            print(file.read_text(encoding="utf-8", errors="replace")[-10000:])
        return 0
    if args.command == "backup":
        if not config.exists():
            print("Runtime configuration is missing", file=sys.stderr)
            return 2
        env = load_env(config, production=True)
        os.environ["PGPASSWORD"] = env["POSTGRES_PASSWORD"]
        out = runtime / "backups" / f"futuredata-{time.strftime('%Y%m%d-%H%M%S')}.sql"
        out.parent.mkdir(parents=True, exist_ok=True)
        return run(
            str(pg / "pg_dump.exe"),
            "-h",
            env["POSTGRES_HOST"],
            "-p",
            env["POSTGRES_PORT"],
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["POSTGRES_DB"],
            "--file",
            str(out),
        ).returncode
    runtime.mkdir(parents=True, exist_ok=True)
    logs.mkdir(exist_ok=True)
    (runtime / "postgres").mkdir(exist_ok=True)
    env = load_env(config, production=True)
    os.environ.update(env)
    os.environ["PGPASSWORD"] = env["POSTGRES_PASSWORD"]
    if not data.exists():
        password_file = runtime / "postgres" / "init-password.txt"
        password_file.write_text(env["POSTGRES_PASSWORD"], encoding="ascii")
        try:
            if run(
                str(pg / "initdb.exe"),
                "-D",
                str(data),
                "-U",
                env["POSTGRES_USER"],
                "--encoding",
                "UTF8",
                "--auth",
                "scram-sha-256",
                "--pwfile",
                str(password_file),
            ).returncode:
                return 1
        finally:
            password_file.unlink(missing_ok=True)
    if run(
        str(ctl),
        "-D",
        str(data),
        "-l",
        str(logs / "postgres.log"),
        "-o",
        f"-h {env['POSTGRES_HOST']} -p {env['POSTGRES_PORT']}",
        "start",
    ).returncode:
        return 1
    run(
        str(pg / "createdb.exe"),
        "-h",
        env["POSTGRES_HOST"],
        "-p",
        env["POSTGRES_PORT"],
        "-U",
        env["POSTGRES_USER"],
        env["POSTGRES_DB"],
    )
    if run(
        str(pg / "psql.exe"),
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        env["POSTGRES_HOST"],
        "-p",
        env["POSTGRES_PORT"],
        "-U",
        env["POSTGRES_USER"],
        "-d",
        env["POSTGRES_DB"],
        "-f",
        str(release / "deploy" / "postgres" / "init" / "001-platform.sql"),
    ).returncode:
        return 1
    with (
        (logs / "appapi.out.log").open("ab") as out,
        (logs / "appapi.err.log").open("ab") as err,
    ):
        process = subprocess.Popen(
            [
                str(release / "python" / "python.exe"),
                "-m",
                "uvicorn",
                "appapi.main:app",
                "--host",
                env["APPAPI_HOST"],
                "--port",
                env["APPAPI_PORT"],
            ],
            cwd=release,
            stdout=out,
            stderr=err,
        )
        pid.write_text(str(process.pid))
    for _ in range(60):
        try:
            if (
                urlopen(
                    f"http://{env['APPAPI_HOST']}:{env['APPAPI_PORT']}/health",
                    timeout=1,
                ).status
                == 200
            ):
                print("FutureData production platform started.")
                return 0
        except OSError:
            time.sleep(0.5)
    stop()
    print("API health check timed out", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
