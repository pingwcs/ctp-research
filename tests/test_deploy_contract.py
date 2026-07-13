"""Contract tests for the private-network platform deployment files."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_platform_compose_exposes_only_loopback_postgres_and_api_ports() -> None:
    compose = _read("deploy/compose.platform.yml")

    assert "postgres:" in compose
    assert "appapi:" in compose
    assert '"127.0.0.1:5432:5432"' in compose
    assert '"127.0.0.1:8000:8000"' in compose
    assert "redis" not in compose.lower()


def test_platform_compose_loads_the_untracked_runtime_environment() -> None:
    compose = _read("deploy/compose.platform.yml")

    assert compose.count("env_file: ${PLATFORM_ENV_FILE}") == 2
    environment = _read("deploy/env/platform.env.example")
    assert "PLATFORM_ENV_FILE=./env/platform.env.example" in environment
    assert "PLATFORM_POSTGRES_DSN" in environment


def test_platform_compose_waits_for_healthy_postgres_before_starting_api() -> None:
    compose = _read("deploy/compose.platform.yml")

    assert "pg_isready" in compose
    assert "condition: service_healthy" in compose


def test_api_image_uses_only_api_dependencies_and_a_non_root_command() -> None:
    dockerfile = _read("deploy/appapi/Dockerfile")

    assert "python:3.12-slim" in dockerfile
    assert "appapi/requirements.txt" in dockerfile
    assert "trade_runtime" not in dockerfile
    assert "node" not in dockerfile.lower()
    assert "USER appapi" in dockerfile
    assert 'CMD ["python", "-m", "appapi.main"]' in dockerfile


def test_platform_compose_includes_loopback_ui_service() -> None:
    compose = _read("deploy/compose.platform.yml")

    assert "appui:" in compose
    assert '"127.0.0.1:5173:8080"' in compose


def test_ui_image_serves_spa_and_proxies_api() -> None:
    dockerfile = _read("deploy/appui/Dockerfile")
    nginx = _read("deploy/appui/default.conf")

    assert "pnpm build" in dockerfile
    assert "nginx-unprivileged" in dockerfile
    assert "location /api/" in nginx
    assert "proxy_pass http://appapi:8000" in nginx
    assert "proxy_http_version 1.1" in nginx
    assert "try_files $uri $uri/ /index.html" in nginx


def test_pipeline_is_an_opt_in_service_with_shared_data_mount() -> None:
    compose = _read("deploy/compose.platform.yml")

    assert "pipeline:" in compose
    assert 'profiles: ["pipeline"]' in compose
    assert "${PLATFORM_DATA_DIR}" in compose
    assert "/workspace/data/output:ro" in compose
    assert ":/data" in compose


def test_pipeline_image_contains_only_pipeline_runtime_dependencies() -> None:
    dockerfile = _read("deploy/pipeline/Dockerfile")

    assert "data_pipeline/requirements.txt" in dockerfile
    assert 'ENTRYPOINT ["python", "data_pipeline/run.py"]' in dockerfile
    assert "appui" not in dockerfile


def test_readme_documents_private_platform_startup_and_pipeline() -> None:
    readme = _read("README.md")

    assert "Docker 私有平台" in readme
    assert "docker compose -f deploy/compose.platform.yml" in readme
    assert "--profile pipeline run --rm pipeline" in readme
    assert "127.0.0.1:5173" in readme


def test_tracked_platform_deployment_files_contain_no_literal_postgres_password() -> None:
    deployment_files = (
        "deploy/compose.platform.yml",
        "deploy/env/platform.env.example",
        "deploy/postgres/init/001-platform.sql",
    )

    for relative_path in deployment_files:
        contents = _read(relative_path).lower()
        assert "postgres_password=change-me" not in contents
        assert "postgresql://ctp_research:change-me@" not in contents

    example = _read("deploy/env/platform.env.example")
    assert "<set-a-local-postgres-password>" in example


def test_initial_schema_is_idempotent() -> None:
    sql = _read("deploy/postgres/init/001-platform.sql")

    assert "CREATE TABLE IF NOT EXISTS auth_users" in sql
