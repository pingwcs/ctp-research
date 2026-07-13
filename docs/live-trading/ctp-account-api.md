# CTP/SimNow Account Connection Contract

The platform accepts CTP credentials only through an owner-only account provisioning interface. The current request model is `CtpAccountConnectionRequest`; production wiring must envelope-encrypt `password` and `auth_code` before persistence. These fields are write-only and must never appear in logs, API responses, database projections, WebSocket events, test output, or Git history.

The non-sensitive example payload is [ctp_simnow_account.example.json](../../appapi/testdata/ctp_simnow_account.example.json). It intentionally uses non-routable `example.invalid` addresses and placeholder secrets. Replace every `REPLACE_*` value and both front addresses with values supplied for the target SimNow account.

| Parameter | Meaning | Source for a real account | Handling rule |
| --- | --- | --- | --- |
| `broker_id` | CTP broker code, for example `9999` in some SimNow environments | SimNow/broker connection page | Store as account configuration |
| `user_id` | Trading account user identifier | SimNow registration | Store as account configuration |
| `password` | Trading password used by the CTP trader API | SimNow registration/reset flow | Write-only `SecretStr`; envelope encrypt |
| `td_front` | Trader API front address in `tcp://host:port` form | SimNow/broker connection page | Store as account configuration; no HTTP/HTTPS URL |
| `md_front` | Market-data API front address in `tcp://host:port` form | SimNow/broker connection page | Store as account configuration; no HTTP/HTTPS URL |
| `app_id` | CTP application identifier for authentication | SimNow/broker connection page | Store as account configuration |
| `auth_code` | CTP authentication code | SimNow/broker connection page | Write-only `SecretStr`; envelope encrypt |
| `product_info` | Optional CTP product/client information | Platform deployment configuration | Non-secret; default `ctp-research` |

Before enabling an account, validate the configuration in this order:

1. Validate request shape and `tcp://` front address syntax.
2. Persist non-sensitive fields and encrypted secret envelopes in one account transaction.
3. Start the account-specific runtime with a short-lived secret mount.
4. Authenticate and log in, then query/confirm the settlement statement under the account's pre-authorization.
5. Query funds, positions, active orders, and trades; only permit orders after reconciliation marks the account ready.

The system must treat the exact front endpoints as environment-specific configuration. They cannot be safely inferred from broker ID alone, and this repository deliberately does not provide live credentials or default SimNow endpoints.
