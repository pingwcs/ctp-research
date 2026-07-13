"""Translate the platform's CTP account contract to vn.py gateway settings."""

from appapi.schemas.trading.accounts import CtpAccountConnectionRequest


def to_vnpy_ctp_settings(
    request: CtpAccountConnectionRequest,
) -> dict[str, str]:
    """Return the exact CTP gateway configuration for a SimNow account.

    The caller must pass this dict directly to the account-isolated runtime and
    must never log the returned value because it contains write-only secrets.
    """
    return {
        "用户名": request.user_id,
        "密码": request.password.get_secret_value(),
        "经纪商代码": request.broker_id,
        "交易服务器": request.td_front,
        "行情服务器": request.md_front,
        "产品名称": request.app_id,
        "授权编码": request.auth_code.get_secret_value(),
        "柜台环境": "测试",
    }
