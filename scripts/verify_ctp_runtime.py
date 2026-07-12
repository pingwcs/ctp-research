"""Verify the CTP runtime image offline or prepare a protected SimNow probe."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


REQUIRED_ONLINE_ENV = (
    "CTP_BROKER_ID",
    "CTP_USER_ID",
    "CTP_PASSWORD",
    "CTP_TD_FRONT",
    "CTP_MD_FRONT",
    "CTP_APP_ID",
    "CTP_AUTH_CODE",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--image-digest")
    args = parser.parse_args(argv)
    try:
        report = offline_report()
    except ModuleNotFoundError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    if args.online:
        report["online"] = online_environment_report()
    if args.image_digest:
        report["image_digest"] = args.image_digest
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("missing_shared_libraries") == [] else 1


def offline_report() -> dict[str, Any]:
    import vnpy_ctp

    package_dir = Path(vnpy_ctp.__file__).resolve().parent
    libraries = sorted(package_dir.rglob("*.so"))
    missing: list[str] = []
    ldd_reports: dict[str, str] = {}
    for library in libraries:
        completed = subprocess.run(
            ["ldd", str(library)],
            check=False,
            capture_output=True,
            text=True,
        )
        output = completed.stdout + completed.stderr
        ldd_reports[str(library)] = output
        if "not found" in output:
            missing.append(str(library))
    return {
        "python": sys.version.split()[0],
        "vnpy": importlib.metadata.version("vnpy"),
        "vnpy_ctp": importlib.metadata.version("vnpy_ctp"),
        "ctp_shared_libraries": [str(item) for item in libraries],
        "ldd": ldd_reports,
        "missing_shared_libraries": missing,
    }


def online_environment_report() -> dict[str, Any]:
    missing = [name for name in REQUIRED_ONLINE_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "online SimNow verification requires: " + ", ".join(missing)
        )
    return {
        "ready": True,
        "broker_id": os.environ["CTP_BROKER_ID"],
        "td_front": os.environ["CTP_TD_FRONT"],
        "md_front": os.environ["CTP_MD_FRONT"],
        "note": "Credentials were present but are intentionally not emitted.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
