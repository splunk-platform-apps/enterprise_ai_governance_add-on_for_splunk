"""Microsoft 365 Copilot audit input via Graph Audit Log Query API.

The Graph audit log query is asynchronous on the Microsoft side. Each run:

1. If a query is pending (checkpointed), poll its status.
   - succeeded: fetch and ingest its records, advance the time window.
   - running/notStarted: exit and try again next interval.
   - failed/cancelled: drop it so a fresh query is submitted.
2. If no query is pending, submit a new query covering
   [last_window_end, now - 15 minutes] and checkpoint its ID.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from splunklib import modularinput as smi

from ai_governance import PROVIDER_MICROSOFT, ST_COPILOT_INTERACTION
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import normalize_copilot_record
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_csv, parse_int, write_json_event
from ai_governance.providers.microsoft_api import MicrosoftGraphAPI

DEFAULT_RECORD_TYPES = ("copilotInteraction",)
INGEST_LAG = timedelta(minutes=15)
MAX_WINDOW = timedelta(hours=24)
MAX_RECORDS_PER_QUERY = 50000


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="copilot_audit",
        collect=_collect,
        sourcetype=ST_COPILOT_INTERACTION,
    )


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


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

    pending_query_id = state.get("pending_query_id")
    if pending_query_id:
        return _handle_pending_query(
            logger,
            api,
            checkpoint,
            ckpt_key,
            state,
            pending_query_id,
            account_name,
            index,
            event_writer,
        )

    return _submit_query(logger, api, checkpoint, ckpt_key, state, input_item)


def _submit_query(logger, api, checkpoint, ckpt_key, state, input_item) -> int:
    backfill_days = min(parse_int(input_item.get("backfill_days"), 7), 180)
    record_types = parse_csv(input_item.get("record_types"), DEFAULT_RECORD_TYPES)

    now = datetime.now(timezone.utc)
    window_end_limit = now - INGEST_LAG

    last_end = state.get("last_window_end")
    if last_end:
        window_start = _parse_iso(last_end)
    else:
        window_start = now - timedelta(days=backfill_days)

    if window_start >= window_end_limit:
        logger.info("Copilot audit window not yet due; skipping this cycle")
        return 0

    window_end = min(window_start + MAX_WINDOW, window_end_limit)
    display_name = "TA-ai-governance %s" % _iso(now)

    query = api.create_audit_query(
        display_name=display_name,
        start_iso=_iso(window_start),
        end_iso=_iso(window_end),
        record_types=record_types,
    )
    query_id = query.get("id")
    if not query_id:
        raise ValueError("Graph audit query submission returned no id")

    checkpoint.update(
        ckpt_key,
        pending_query_id=query_id,
        pending_window_start=_iso(window_start),
        pending_window_end=_iso(window_end),
    )
    logger.info(
        "Submitted Copilot audit query %s for window %s - %s",
        query_id,
        _iso(window_start),
        _iso(window_end),
    )
    return 0


def _handle_pending_query(
    logger,
    api,
    checkpoint,
    ckpt_key,
    state,
    query_id,
    account_name,
    index,
    event_writer,
) -> int:
    query = api.get_audit_query(query_id)
    status = (query.get("status") or "").lower()

    if status in ("notstarted", "running"):
        logger.info("Copilot audit query %s still %s", query_id, status)
        return 0

    if status != "succeeded":
        logger.warning(
            "Copilot audit query %s finished with status %s; resubmitting window",
            query_id,
            status,
        )
        checkpoint.update(ckpt_key, pending_query_id=None)
        return 0

    count = 0
    for record in api.iter_audit_records(query_id, max_items=MAX_RECORDS_PER_QUERY):
        normalized = normalize_copilot_record(record)
        write_json_event(
            event_writer=event_writer,
            payload=normalized,
            index=index,
            sourcetype=ST_COPILOT_INTERACTION,
            source="aigov:copilot:audit:%s" % account_name,
            event_time=record.get("createdDateTime"),
        )
        count += 1

    checkpoint.update(
        ckpt_key,
        pending_query_id=None,
        pending_window_start=None,
        pending_window_end=None,
        last_window_end=state.get("pending_window_end"),
    )
    logger.info("Ingested %s Copilot audit records from query %s", count, query_id)
    return count
