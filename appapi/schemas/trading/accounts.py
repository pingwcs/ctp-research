"""CTP account connection contracts; secret values are write-only."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class CtpAccountConnectionRequest(BaseModel):
    """Parameters required to connect one tenant-owned CTP account.

    This request is accepted only by an account-owner provisioning endpoint.
    `password` and `auth_code` must be envelope-encrypted immediately and are
    never returned by any response schema.
    """

    model_config = ConfigDict(extra="forbid")

    broker_id: str = Field(min_length=1, max_length=32)
    user_id: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=256)
    td_front: str = Field(min_length=8, max_length=256)
    md_front: str = Field(min_length=8, max_length=256)
    app_id: str = Field(min_length=1, max_length=128)
    auth_code: SecretStr = Field(min_length=1, max_length=256)
    product_info: str = Field(default="", max_length=128)

    @field_validator("td_front", "md_front")
    @classmethod
    def validate_tcp_front(cls, value: str) -> str:
        if not value.startswith("tcp://"):
            raise ValueError("CTP front address must use tcp://")
        host_port = value.removeprefix("tcp://")
        if ":" not in host_port or host_port.endswith(":"):
            raise ValueError("CTP front address must include host and port")
        return value
