import pytest
from pydantic import ValidationError

from appapi.schemas.trading.accounts import CtpAccountConnectionRequest


def test_ctp_connection_request_accepts_simnow_placeholder_configuration():
    request = CtpAccountConnectionRequest(
        broker_id="9999",
        user_id="simnow-test-user",
        password="not-a-real-password",
        td_front="tcp://td.example.invalid:41205",
        md_front="tcp://md.example.invalid:41213",
        app_id="simnow_client_test",
        auth_code="not-a-real-auth-code",
    )

    assert request.td_front.startswith("tcp://")
    assert request.password.get_secret_value() == "not-a-real-password"


def test_ctp_connection_request_rejects_unsupported_front_scheme():
    with pytest.raises(ValidationError, match="tcp"):
        CtpAccountConnectionRequest(
            broker_id="9999",
            user_id="simnow-test-user",
            password="not-a-real-password",
            td_front="https://td.example.invalid",
            md_front="tcp://md.example.invalid:41213",
            app_id="simnow_client_test",
            auth_code="not-a-real-auth-code",
        )
