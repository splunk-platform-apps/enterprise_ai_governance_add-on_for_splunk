"""Account credential loading from Splunk encrypted storage."""

from __future__ import annotations

from typing import Any

from solnlib import conf_manager

from ai_governance import ACCOUNT_CONF, ADDON_NAME

_ACCOUNT_FIELDS = (
    "provider",
    "anthropic_admin_key",
    "anthropic_analytics_key",
    "openai_admin_key",
    "google_client_id",
    "google_client_secret",
    "google_refresh_token",
    "google_customer_id",
    "ms_tenant_id",
    "ms_client_id",
    "ms_client_secret",
    "sh_base_url",
    "sh_server_type",
    "sh_api_key",
    "sh_allow_http",
    "proxy_url",
)


def get_account_config(session_key: str, account_name: str) -> dict[str, Any]:
    """Load an account stanza including decrypted credential fields."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ACCOUNT_CONF}",
    )
    account_conf = cfm.get_conf(ACCOUNT_CONF)
    stanza = account_conf.get(account_name)
    account = {"name": account_name}
    for field in _ACCOUNT_FIELDS:
        value = stanza.get(field)
        account[field] = value if value not in ("", None, "None") else None
    return account


def require_provider(account: dict[str, Any], expected_provider: str) -> None:
    provider = account.get("provider")
    if provider != expected_provider:
        raise ValueError(
            "Account '{}' has provider '{}' but this input requires provider '{}'. "
            "Select a matching account on the input.".format(
                account.get("name"), provider, expected_provider
            )
        )


def require_fields(account: dict[str, Any], *fields: str) -> None:
    missing = [field for field in fields if not account.get(field)]
    if missing:
        raise ValueError(
            "Account '{}' is missing required credential field(s): {}".format(
                account.get("name"), ", ".join(missing)
            )
        )
