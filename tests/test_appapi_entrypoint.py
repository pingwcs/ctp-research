from appapi.main import resolve_listen_host


def test_resolve_listen_host_defaults_to_loopback() -> None:
    assert resolve_listen_host({}) == "127.0.0.1"


def test_resolve_listen_host_empty_value_defaults_to_loopback() -> None:
    assert resolve_listen_host({"APPAPI_HOST": ""}) == "127.0.0.1"


def test_resolve_listen_host_uses_explicit_environment_value() -> None:
    assert resolve_listen_host({"APPAPI_HOST": "0.0.0.0"}) == "0.0.0.0"
