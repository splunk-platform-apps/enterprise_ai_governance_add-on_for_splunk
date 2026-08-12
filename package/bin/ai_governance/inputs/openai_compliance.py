"""OpenAI ChatGPT Enterprise Compliance Logs input.

Collects the immutable, time-windowed JSONL log files published by the
OpenAI Compliance Logs Platform. This covers end-user activity in ChatGPT
Enterprise - the plane that ``openai_audit`` does not see, since that input
reports on API platform administration instead.

The platform retains roughly 30 days of history, so this input exists to
move that data into Splunk before it ages out.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from splunklib import modularinput as smi

from ai_governance import PROVIDER_OPENAI, ST_OPENAI_COMPLIANCE
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import compliance_event_time, normalize_openai_compliance
from ai_governance.http_client import APIError
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_bool, parse_csv, parse_int, write_json_event
from ai_governance.providers.openai_compliance_api import (
    OpenAIComplianceAPI,
    parse_jsonl,
)

# Compliance Logs Platform retention. Asking for more history than this just
# produces empty pages, so the backfill window is capped here.
MAX_BACKFILL_DAYS = 30

DEFAULT_EVENT_TYPES = ("AUTH_LOG",)

_AUTH_REMEDIATION = (
    "OpenAI rejected the configured Compliance API credential (HTTP %s): %s - "
    "this input needs a ChatGPT Enterprise Compliance API key, which is not "
    "the same as the platform Admin API key (sk-admin-...) used by the OpenAI "
    "Audit Logs input. An Organization Owner must create it and OpenAI must "
    "approve the Compliance API scopes on it. Also confirm the workspace or "
    "organization ID on the account matches the key."
)


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="openai_compliance",
        collect=_collect,
        sourcetype=ST_OPENAI_COMPLIANCE,
    )


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_OPENAI)
    require_fields(account, "openai_compliance_key", "openai_compliance_principal_id")

    api = OpenAIComplianceAPI(
        compliance_key=account["openai_compliance_key"],
        principal_id=account["openai_compliance_principal_id"],
        proxy_url=account.get("proxy_url"),
    )
    checkpoint = CheckpointStore(session_key)
    base_key = stanza_key(input_key)

    event_types = parse_csv(input_item.get("event_types"), DEFAULT_EVENT_TYPES)
    if not event_types:
        logger.warning("No event types configured; nothing to collect")
        return 0

    backfill_days = min(
        parse_int(input_item.get("backfill_days"), 7), MAX_BACKFILL_DAYS
    )
    max_files = parse_int(input_item.get("max_files_per_cycle"), 200)
    include_content = parse_bool(input_item.get("include_message_content"), False)
    index = input_item.get("index")

    total = 0
    for event_type in event_types:
        try:
            total += _collect_event_type(
                logger=logger,
                api=api,
                checkpoint=checkpoint,
                ckpt_key=f"{base_key}:{event_type}",
                event_type=event_type,
                account_name=account_name,
                index=index,
                backfill_days=backfill_days,
                max_files=max_files,
                include_content=include_content,
                event_writer=event_writer,
            )
        except APIError as exc:
            if exc.status_code in (401, 403):
                # Credential problems affect every event type - fail loudly
                # rather than logging the same error once per type.
                logger.error(_AUTH_REMEDIATION, exc.status_code, exc)
                raise
            logger.warning(
                "Skipping event type '%s' (HTTP %s): %s - confirm this event "
                "type is available to your workspace in the Compliance API "
                "reference; other configured event types are unaffected",
                event_type,
                exc.status_code,
                exc,
            )
        except Exception as exc:
            # The watermark for this type has not advanced past the failure,
            # so the next cycle retries it without a gap.
            logger.warning(
                "Collection failed for event type '%s': %s - will retry next "
                "interval; other configured event types are unaffected",
                event_type,
                exc,
            )

    return total


def _collect_event_type(
    logger,
    api,
    checkpoint,
    ckpt_key,
    event_type,
    account_name,
    index,
    backfill_days,
    max_files,
    include_content,
    event_writer,
) -> int:
    state = checkpoint.get(ckpt_key)
    after = state.get("last_end_time")
    if not after:
        after = (datetime.now(timezone.utc) - timedelta(days=backfill_days)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        logger.info(
            "No checkpoint for event type '%s'; backfilling %s day(s) from %s",
            event_type,
            backfill_days,
            after,
        )

    source = f"aigov:openai:compliance:{account_name}"
    files_done = 0
    records = 0
    truncated = False

    for files, last_end_time, _has_more in api.iter_log_pages(event_type, after):
        page_complete = True
        for descriptor in files:
            if files_done >= max_files:
                page_complete = False
                truncated = True
                break

            file_id = descriptor.get("id")
            if not file_id:
                continue

            body = api.download_log(file_id)
            for record in parse_jsonl(body):
                normalized = normalize_openai_compliance(
                    record, event_type, include_content=include_content
                )
                write_json_event(
                    event_writer=event_writer,
                    payload=normalized,
                    index=index,
                    sourcetype=ST_OPENAI_COMPLIANCE,
                    source=source,
                    event_time=compliance_event_time(record)
                    or descriptor.get("end_time"),
                )
                records += 1
            files_done += 1

        # Advance the watermark only once every file in the page has been
        # emitted, so an interrupted cycle resumes without losing a window.
        if page_complete and last_end_time:
            checkpoint.update(ckpt_key, last_end_time=last_end_time)

        if truncated:
            break

    if truncated:
        logger.warning(
            "Hit max_files_per_cycle (%s) for event type '%s'; the checkpoint "
            "was not advanced past the partial page, so collection resumes "
            "there next interval - raise max_files_per_cycle to catch up faster",
            max_files,
            event_type,
        )
    if records:
        logger.info(
            "Ingested %s '%s' compliance records from %s log file(s)",
            records,
            event_type,
            files_done,
        )
    return records
