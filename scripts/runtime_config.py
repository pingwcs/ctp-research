"""Small, validated interface for launcher environment files."""

from pathlib import Path


class ConfigError(ValueError):
    pass


REQUIRED = {
    "APPAPI_HOST",
    "APPAPI_PORT",
    "UI_HOST",
    "UI_PORT",
    "MARKET_DATA_DIR",
    "MARKET_LOG_DIR",
    "APPUI_DIST_DIR",
    "RUNTIME_ROOT",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "PLATFORM_POSTGRES_DSN",
    "AUTH_TOKEN_SECRET",
}
PATH_KEYS = {"MARKET_DATA_DIR", "MARKET_LOG_DIR", "APPUI_DIST_DIR", "RUNTIME_ROOT"}


def load_env(path: Path, production: bool) -> dict[str, str]:
    if not path.is_file():
        raise ConfigError(f"Configuration file is missing: {path}")
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"Invalid configuration line: {raw}")
        key, value = line.split("=", 1)
        if key in values:
            raise ConfigError(f"Duplicate configuration key: {key}")
        values[key] = value.strip()
    missing = REQUIRED - values.keys()
    if missing:
        raise ConfigError(f"Missing configuration keys: {', '.join(sorted(missing))}")
    if production and any(
        values[key] == "CHANGE_ME" for key in ("POSTGRES_PASSWORD", "AUTH_TOKEN_SECRET")
    ):
        raise ConfigError("Production secrets must replace CHANGE_ME in prod.env")
    for key in PATH_KEYS & values.keys():
        values[key] = str((path.parent / values[key]).resolve())
    return values
