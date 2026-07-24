"""Google Gemini (Workspace) audit input via Admin SDK Reports API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from splunklib import modularinput as smi

from ai_governance import PROVIDER_GEMINI, ST_GEMINI_AUDIT
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import normalize_gemini_activity
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_csv, parse_int, write_json_event
from ai_governance.providers.google_api import GoogleReportsAPI

DEFAULT_APPLICATIONS = ("gemini_in_workspace_apps",)


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="gemini_audit",
        collect=_collect,
        sourcetype=ST_GEMINI_AUDIT,
    )


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_GEMINI)
    require_fields(
        account, "google_client_id", "google_client_secret", "google_refresh_token"
    )

    api = GoogleReportsAPI(
        client_id=account["google_client_id"],
        client_secret=account["google_client_secret"],
        refresh_token=account["google_refresh_token"],
        proxy_url=account.get("proxy_url"),
    )
    checkpoint = CheckpointStore(session_key)
    ckpt_key = stanza_key(input_key)
    state = checkpoint.get(ckpt_key)

    max_events = parse_int(input_item.get("max_events_per_cycle"), 5000)
    backfill_days = min(parse_int(input_item.get("backfill_days"), 7), 180)
    applications = parse_csv(input_item.get("applications"), DEFAULT_APPLICATIONS)
    customer_id = account.get("google_customer_id") or "my_customer"
    index = input_item.get("index")

    total = 0
    for application in applications:
        app_state_key = "last_time_%s" % application
        start_time = state.get(app_state_key)
        if not start_time:
            start_time = _iso(
                datetime.now(timezone.utc) - timedelta(days=backfill_days)
            )

        # API returns newest first; track max item time and dedupe boundary
        # by advancing startTime 1ms past the newest previously seen event.
        max_time = start_time
        count = 0
        for item in api.list_activities(
            application_name=application,
            start_time=start_time,
            customer_id=customer_id,
            max_items=max_events,
        ):
            item_time = (item.get("id") or {}).get("time")
            if item_time and item_time <= start_time:
                continue  # boundary duplicate
            normalized = normalize_gemini_activity(item)
            write_json_event(
                event_writer=event_writer,
                payload=normalized,
                index=index,
                sourcetype=ST_GEMINI_AUDIT,
                source="aigov:gemini:%s:%s" % (application, account_name),
                event_time=item_time,
            )
            count += 1
            if item_time and item_time > max_time:
                max_time = item_time

        if count:
            checkpoint.update(ckpt_key, **{app_state_key: max_time})
            logger.info(
                "Ingested %s Gemini audit events for application %s",
                count,
                application,
            )
        if count >= max_events:
            logger.warning(
                "Hit max_events_per_cycle (%s) for application %s; the API "
                "returns newest events first, so older events in this window "
                "may be skipped - raise max_events_per_cycle for large "
                "backfills",
                max_events,
                application,
            )
        total += count

    return total
