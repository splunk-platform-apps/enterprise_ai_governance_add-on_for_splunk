"""Anthropic Compliance Activity Feed + directory input."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from splunklib import modularinput as smi

from ai_governance import (
    PROVIDER_ANTHROPIC,
    ST_ANTHROPIC_ACTIVITY,
    ST_ANTHROPIC_GROUP,
    ST_ANTHROPIC_USER,
)
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import envelope, normalize_anthropic_activity
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_bool, parse_int, write_json_event
from ai_governance.providers.anthropic_api import AnthropicAPI

DIRECTORY_SNAPSHOT_SECONDS = 12 * 3600


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="anthropic_compliance",
        collect=_collect,
        sourcetype=ST_ANTHROPIC_ACTIVITY,
    )


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_ANTHROPIC)
    require_fields(account, "anthropic_admin_key")

    api = AnthropicAPI(
        admin_key=account["anthropic_admin_key"],
        analytics_key=account.get("anthropic_analytics_key"),
        proxy_url=account.get("proxy_url"),
    )
    checkpoint = CheckpointStore(session_key)
    ckpt_key = stanza_key(input_key)
    state = checkpoint.get(ckpt_key)

    max_events = parse_int(input_item.get("max_events_per_cycle"), 2000)
    backfill_days = min(parse_int(input_item.get("backfill_days"), 7), 180)
    index = input_item.get("index")

    after_id = state.get("last_activity_id")
    created_at_gte = None
    if not after_id:
        created_at_gte = (
            datetime.now(timezone.utc) - timedelta(days=backfill_days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

    count = 0
    last_activity_id = after_id
    last_created_at = state.get("last_created_at")

    for activity in api.list_activities(
        after_id=after_id, created_at_gte=created_at_gte, max_items=max_events
    ):
        normalized = normalize_anthropic_activity(activity)
        write_json_event(
            event_writer=event_writer,
            payload=normalized,
            index=index,
            sourcetype=ST_ANTHROPIC_ACTIVITY,
            source="anthropic:activities:%s" % account_name,
            event_time=normalized.get("created_at"),
        )
        count += 1
        last_activity_id = activity.get("id", last_activity_id)
        last_created_at = activity.get("created_at", last_created_at)

    if count:
        checkpoint.update(
            ckpt_key,
            last_activity_id=last_activity_id,
            last_created_at=last_created_at,
        )
        logger.info("Ingested %s Anthropic compliance activities", count)

    if parse_bool(input_item.get("collect_directory"), True):
        count += _collect_directory(
            logger, api, checkpoint, ckpt_key, account_name, index, event_writer
        )

    return count


def _collect_directory(
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
            provider=PROVIDER_ANTHROPIC,
            category="directory",
            action="user_snapshot",
            user=user.get("email") or user.get("email_address"),
        )
        write_json_event(
            event_writer=event_writer,
            payload=payload,
            index=index,
            sourcetype=ST_ANTHROPIC_USER,
            source="anthropic:directory:%s" % account_name,
            event_time=snapshot_time,
        )
        count += 1

    try:
        for group in api.list_groups():
            payload = envelope(
                dict(group, snapshot_time=snapshot_time),
                provider=PROVIDER_ANTHROPIC,
                category="directory",
                action="group_snapshot",
            )
            write_json_event(
                event_writer=event_writer,
                payload=payload,
                index=index,
                sourcetype=ST_ANTHROPIC_GROUP,
                source="anthropic:directory:%s" % account_name,
                event_time=snapshot_time,
            )
            count += 1
    except Exception as exc:  # groups endpoint may be unavailable for some plans
        logger.info("Skipping Anthropic groups snapshot: %s", exc)

    checkpoint.update(ckpt_key, last_directory_snapshot=now)
    if count:
        logger.info("Ingested %s Anthropic directory records", count)
    return count
