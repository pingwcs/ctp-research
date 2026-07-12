import os

import pytest

from scripts.verify_ctp_runtime import (
    REQUIRED_ONLINE_ENV,
    main,
    online_environment_report,
)


def test_online_report_rejects_missing_simnow_credentials(monkeypatch):
    for name in REQUIRED_ONLINE_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="CTP_BROKER_ID"):
        online_environment_report()


def test_online_report_redacts_password_and_auth_code(monkeypatch):
    values = {
        "CTP_BROKER_ID": "9999",
        "CTP_USER_ID": "user-1",
        "CTP_PASSWORD": "do-not-print",
        "CTP_TD_FRONT": "tcp://td.example:1",
        "CTP_MD_FRONT": "tcp://md.example:2",
        "CTP_APP_ID": "app-1",
        "CTP_AUTH_CODE": "do-not-print-auth-code",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    report = online_environment_report()
    serialized = str(report)

    assert report["ready"] is True
    assert values["CTP_PASSWORD"] not in serialized
    assert values["CTP_AUTH_CODE"] not in serialized
    assert os.environ["CTP_USER_ID"] == "user-1"


def test_main_returns_structured_error_when_vnpy_ctp_is_not_installed(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        "scripts.verify_ctp_runtime.offline_report",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("vnpy_ctp")),
    )

    assert main([]) == 2
    assert '"error": "vnpy_ctp"' in capsys.readouterr().out
