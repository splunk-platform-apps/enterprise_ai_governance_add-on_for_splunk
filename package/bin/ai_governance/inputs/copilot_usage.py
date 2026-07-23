"""Microsoft 365 Copilot usage report input via Graph reports API."""

from __future__ import annotations

from splunklib import modularinput as smi

from ai_governance import PROVIDER_MICROSOFT, ST_COPILOT_USAGE
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import envelope
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import write_json_event
from ai_governance.providers.microsoft_api import MicrosoftGraphAPI

VALID_PERIODS = ("D7", "D30", "D90", "D180")


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="copilot_usage",
        collect=_collect,
        sourcetype=ST_COPILOT_USAGE,
    )


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_MICROSOFT)
    require_fields(account, "ms_tenant_id", "ms_client_id", "ms_client_secret")

    api = MicrosoftGraphAPI(
        tenant_id=account["ms_tenant_id"],
        client_id=account["ms_client_id"],
        client_secret=account["ms_client_secret"],
        proxy_url=account.get("proxy_url"),
    )
    checkpoint = CheckpointStore(session_key)
    ckpt_key = stanza_key(input_key)
    state = checkpoint.get(ckpt_key)
    index = input_item.get("index")

    period = input_item.get("period") or "D7"
    if period not in VALID_PERIODS:
        period = "D7"

    rows = api.copilot_usage_user_detail(period=period)
    if not rows:
        logger.info("No Copilot usage rows returned")
        return 0

    refresh_date = rows[0].get("reportRefreshDate")
    if refresh_date and state.get("last_report_refresh_date") == refresh_date:
        logger.info(
            "Copilot usage report for %s already ingested; skipping", refresh_date
        )
        return 0

    count = 0
    for row in rows:
        payload = envelope(
            dict(row, report_period=period),
            provider=PROVIDER_MICROSOFT,
            category="usage",
            user=row.get("userPrincipalName"),
        )
        event_time = None
        if row.get("reportRefreshDate"):
            event_time = "%sT00:00:00Z" % row["reportRefreshDate"]
        write_json_event(
            event_writer=event_writer,
            payload=payload,
            index=index,
            sourcetype=ST_COPILOT_USAGE,
            source="aigov:copilot:usage:%s" % account_name,
            event_time=event_time,
        )
        count += 1

    if refresh_date:
        checkpoint.update(ckpt_key, last_report_refresh_date=refresh_date)
    logger.info("Ingested %s Copilot usage rows", count)
    return count
