"""Anthropic usage / cost / adoption analytics input."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from splunklib import modularinput as smi

from ai_governance import (
    PROVIDER_ANTHROPIC,
    ST_ANTHROPIC_COST,
    ST_ANTHROPIC_SUMMARY,
    ST_ANTHROPIC_USAGE,
)
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import envelope
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_bool, parse_int, write_json_event
from ai_governance.providers.anthropic_api import AnthropicAPI


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="anthropic_analytics",
        collect=_collect,
        sourcetype=ST_ANTHROPIC_USAGE,
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

    lookback_days = min(parse_int(input_item.get("lookback_days"), 7), 90)
    index = input_item.get("index")

    # Analytics data is finalized with a delay; collect through yesterday.
    # Each collector resumes from its own checkpoint so a given day is
    # ingested exactly once (re-pulling the window would multiply sums).
    ending = date.today() - timedelta(days=1)
    default_start = ending - timedelta(days=lookback_days - 1)
    ending_date = ending.isoformat()

    count = 0
    collectors = (
        ("collect_usage", api.analytics_usage, ST_ANTHROPIC_USAGE, "usage"),
        ("collect_cost", api.analytics_cost, ST_ANTHROPIC_COST, "cost"),
        ("collect_summaries", api.analytics_summaries, ST_ANTHROPIC_SUMMARY, "summary"),
    )
    for flag, fetch, sourcetype, category in collectors:
        if not parse_bool(input_item.get(flag), True):
            continue
        starting = _resume_date(state, category, default_start)
        if starting > ending:
            logger.info("Anthropic analytics %s already current", category)
            continue
        starting_date = starting.isoformat()
        try:
            for item in fetch(starting_date, ending_date):
                event_date = (
                    item.get("date")
                    or item.get("starting_date")
                    or item.get("starting_at")
                    or item.get("bucket")
                    or ending_date
                )
                payload = envelope(
                    dict(item),
                    provider=PROVIDER_ANTHROPIC,
                    category=category,
                    user=item.get("email") or item.get("actor_email"),
                )
                write_json_event(
                    event_writer=event_writer,
                    payload=payload,
                    index=index,
                    sourcetype=sourcetype,
                    source="anthropic:analytics:%s" % account_name,
                    event_time="%sT00:00:00Z" % event_date
                    if len(str(event_date)) == 10
                    else event_date,
                )
                count += 1
        except Exception as exc:
            # Leave this collector's checkpoint untouched so the window is
            # retried next run rather than silently skipped.
            logger.warning(
                "Anthropic analytics %s collection failed: %s", category, exc
            )
            continue
        checkpoint.update(ckpt_key, **{"last_ending_%s" % category: ending_date})

    logger.info("Ingested %s Anthropic analytics records", count)
    return count


def _resume_date(state: Dict[str, Any], category: str, default_start: date) -> date:
    """Day after the last day this collector ingested, floored at the
    lookback default. Falls back to the legacy shared key if present."""
    last = state.get("last_ending_%s" % category) or state.get("last_ending_date")
    if last:
        try:
            resumed = date.fromisoformat(str(last)) + timedelta(days=1)
            if resumed > default_start:
                return resumed
        except ValueError:
            pass
    return default_start
