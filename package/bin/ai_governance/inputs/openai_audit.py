"""OpenAI organization audit log + user directory input."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from splunklib import modularinput as smi

from ai_governance import PROVIDER_OPENAI, ST_OPENAI_AUDIT, ST_OPENAI_USER
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import envelope, normalize_openai_audit
from ai_governance.http_client import APIError
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_bool, parse_int, write_json_event
from ai_governance.providers.openai_api import OpenAIAPI

DIRECTORY_SNAPSHOT_SECONDS = 12 * 3600


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="openai_audit",
        collect=_collect,
        sourcetype=ST_OPENAI_AUDIT,
    )


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_OPENAI)
    require_fields(account, "openai_admin_key")

    api = OpenAIAPI(
        admin_key=account["openai_admin_key"], proxy_url=account.get("proxy_url")
    )
    checkpoint = CheckpointStore(session_key)
    ckpt_key = stanza_key(input_key)
    state = checkpoint.get(ckpt_key)

    max_events = parse_int(input_item.get("max_events_per_cycle"), 2000)
    backfill_days = min(parse_int(input_item.get("backfill_days"), 7), 180)
    index = input_item.get("index")

    last_effective_at = state.get("last_effective_at")
    if last_effective_at is None:
        last_effective_at = int(time.time()) - backfill_days * 86400

    # The audit log API returns newest first; collect then checkpoint max.
    count = 0
    max_seen = int(last_effective_at)
    try:
        for record in api.list_audit_logs(
            effective_at_gt=int(last_effective_at), max_items=max_events
        ):
            normalized = normalize_openai_audit(record)
            write_json_event(
                event_writer=event_writer,
                payload=normalized,
                index=index,
                sourcetype=ST_OPENAI_AUDIT,
                source="aigov:openai:audit:%s" % account_name,
                event_time=record.get("effective_at"),
            )
            count += 1
            effective_at = record.get("effective_at")
            if isinstance(effective_at, (int, float)) and effective_at > max_seen:
                max_seen = int(effective_at)
    except APIError as exc:
        if exc.status_code in (401, 403):
            logger.error(
                "OpenAI rejected the configured key (HTTP %s): %s - the audit "
                "logs API requires an organization Admin API key (sk-admin-...) "
                "created by an organization Owner under platform.openai.com "
                "Settings > Organization > Admin keys; project keys (sk-proj-...) "
                "and keys minted without the api.audit_logs.read scope cannot "
                "read audit logs",
                exc.status_code,
                exc,
            )
        raise

    if count:
        checkpoint.update(ckpt_key, last_effective_at=max_seen)
        logger.info("Ingested %s OpenAI audit log events", count)
    if count >= max_events:
        logger.warning(
            "Hit max_events_per_cycle (%s); the API returns newest events "
            "first, so older events in this window may be skipped - raise "
            "max_events_per_cycle for large backfills",
            max_events,
        )

    if parse_bool(input_item.get("collect_users"), True):
        try:
            count += _collect_users(
                logger, api, checkpoint, ckpt_key, account_name, index, event_writer
            )
        except Exception as exc:
            logger.warning(
                "OpenAI user directory snapshot failed: %s - audit log "
                "collection is unaffected; the users API needs an additional "
                "read scope on the admin key",
                exc,
            )

    return count


def _collect_users(
    logger, api, checkpoint, ckpt_key, account_name, index, event_writer
) -> int:
    state = checkpoint.get(ckpt_key)
    last_snapshot = float(state.get("last_directory_snapshot") or 0)
    now = time.time()
    if now - last_snapshot < DIRECTORY_SNAPSHOT_SECONDS:
        return 0

    count = 0
    snapshot_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for user in api.list_users():
        payload = envelope(
            dict(user, snapshot_time=snapshot_time),
            provider=PROVIDER_OPENAI,
            category="directory",
            action="user_snapshot",
            user=user.get("email"),
        )
        write_json_event(
            event_writer=event_writer,
            payload=payload,
            index=index,
            sourcetype=ST_OPENAI_USER,
            source="aigov:openai:directory:%s" % account_name,
            event_time=snapshot_time,
        )
        count += 1

    checkpoint.update(ckpt_key, last_directory_snapshot=now)
    if count:
        logger.info("Ingested %s OpenAI user records", count)
    return count
