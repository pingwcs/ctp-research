from appapi.schemas.trading.accounts import CtpAccountConnectionRequest
from appapi.services.trading.ctp_settings import to_vnpy_ctp_settings


def test_ctp_api_contract_maps_to_vnpy_ctp_simnow_settings():
    request = CtpAccountConnectionRequest(
        broker_id="9999",
        user_id="simnow-test-user",
        password="not-a-real-password",
        td_front="tcp://td.example.invalid:41205",
        md_front="tcp://md.example.invalid:41213",
        app_id="simnow_client_test",
        auth_code="not-a-real-auth-code",
        product_info="ctp-research",
    )

    settings = to_vnpy_ctp_settings(request)

    assert settings == {
        "用户名": "simnow-test-user",
        "密码": "not-a-real-password",
        "经纪商代码": "9999",
        "交易服务器": "tcp://td.example.invalid:41205",
        "行情服务器": "tcp://md.example.invalid:41213",
        "产品名称": "simnow_client_test",
        "授权编码": "not-a-real-auth-code",
        "柜台环境": "测试",
    }
