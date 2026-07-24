"""Self-hosted / open-source LLM server monitor input.

Governance signals collected per cycle:

- **Health**: reachability + latency of the model-list endpoint
  (``aigov:selfhosted:health``; a "down" event is emitted on failure).
- **Model inventory**: snapshot of served models at most every 12 hours
  (``aigov:selfhosted:model``) plus immediate ``model_added`` /
  ``model_removed`` audit events whenever the set changes
  (``aigov:selfhosted:audit``) — catches unapproved model deployments.
- **Runtime state** (Ollama): currently loaded models
  (``aigov:selfhosted:runtime``).
- **Prometheus metrics** (vLLM / LiteLLM): request/token counters
  (``aigov:selfhosted:metric``).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from splunklib import modularinput as smi

from ai_governance import (
    PROVIDER_SELFHOSTED,
    ST_SELFHOSTED_AUDIT,
    ST_SELFHOSTED_HEALTH,
    ST_SELFHOSTED_METRIC,
    ST_SELFHOSTED_MODEL,
    ST_SELFHOSTED_RUNTIME,
)
from ai_governance.account import get_account_config, require_fields, require_provider
from ai_governance.checkpoint import CheckpointStore
from ai_governance.events import envelope
from ai_governance.inputs.base import run_input, stanza_key
from ai_governance.input_utils import parse_bool, parse_csv, write_json_event
from ai_governance.providers.selfhosted_api import PROMETHEUS_SERVERS, SelfHostedAPI

MODEL_SNAPSHOT_SECONDS = 12 * 3600
MAX_METRIC_SAMPLES = 5000


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    run_input(
        inputs,
        event_writer,
        input_type="selfhosted_monitor",
        collect=_collect,
        sourcetype=ST_SELFHOSTED_MODEL,
    )


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect(logger, session_key, input_key, input_item, event_writer) -> int:
    account_name = input_item.get("account")
    account = get_account_config(session_key, account_name)
    require_provider(account, PROVIDER_SELFHOSTED)
    require_fields(account, "sh_base_url")

    api = SelfHostedAPI(
        base_url=account["sh_base_url"],
        server_type=account.get("sh_server_type") or "openai_compatible",
        api_key=account.get("sh_api_key"),
        allow_http=parse_bool(account.get("sh_allow_http"), False),
        proxy_url=account.get("proxy_url"),
    )
    checkpoint = CheckpointStore(session_key)
    ckpt_key = stanza_key(input_key)
    state = checkpoint.get(ckpt_key)
    index = input_item.get("index")
    source = "aigov:selfhosted:%s" % account_name
    now_iso = _now_iso()
    count = 0

    # -- Health + model inventory (the models call doubles as the probe) ----
    models = None
    if parse_bool(input_item.get("collect_models"), True):
        try:
            models, latency = api.list_models()
            health = {
                "status": "up",
                "response_time_ms": round(latency * 1000, 1),
                "model_count": len(models),
                "server_type": api.server_type,
                "base_url": account["sh_base_url"],
            }
        except Exception as exc:
            health = {
                "status": "down",
                "error": str(exc),
                "server_type": api.server_type,
                "base_url": account["sh_base_url"],
            }
            logger.warning("Self-hosted server unreachable: %s", exc)
        write_json_event(
            event_writer=event_writer,
            payload=envelope(
                health,
                provider=PROVIDER_SELFHOSTED,
                category="health",
                action="health_check",
            ),
            index=index,
            sourcetype=ST_SELFHOSTED_HEALTH,
            source=source,
            event_time=now_iso,
        )
        count += 1

    if models is not None:
        count += _process_inventory(
            logger,
            models,
            api,
            state,
            checkpoint,
            ckpt_key,
            account["sh_base_url"],
            index,
            source,
            event_writer,
            now_iso,
        )

    # -- Runtime state (Ollama loaded models) -------------------------------
    if api.server_type == "ollama" and parse_bool(
        input_item.get("collect_runtime"), True
    ):
        try:
            for running in api.running_models():
                payload = envelope(
                    dict(running, base_url=account["sh_base_url"]),
                    provider=PROVIDER_SELFHOSTED,
                    category="runtime",
                    action="model_running",
                )
                write_json_event(
                    event_writer=event_writer,
                    payload=payload,
                    index=index,
                    sourcetype=ST_SELFHOSTED_RUNTIME,
                    source=source,
                    event_time=now_iso,
                )
                count += 1
        except Exception as exc:
            logger.warning("Runtime state collection failed: %s", exc)

    # -- Prometheus metrics ---------------------------------------------------
    if api.server_type in PROMETHEUS_SERVERS and parse_bool(
        input_item.get("collect_metrics"), True
    ):
        prefixes = parse_csv(
            input_item.get("metrics_prefixes"), ("vllm:", "litellm_", "ollama_")
        )
        metrics_path = input_item.get("metrics_path") or "/metrics"
        try:
            emitted = 0
            for sample in api.scrape_metrics(metrics_path, prefixes):
                payload = envelope(
                    dict(sample, base_url=account["sh_base_url"]),
                    provider=PROVIDER_SELFHOSTED,
                    category="metrics",
                    action=sample.get("metric_name"),
                )
                write_json_event(
                    event_writer=event_writer,
                    payload=payload,
                    index=index,
                    sourcetype=ST_SELFHOSTED_METRIC,
                    source=source,
                    event_time=now_iso,
                )
                emitted += 1
                if emitted >= MAX_METRIC_SAMPLES:
                    logger.warning(
                        "Metric sample cap (%s) reached; narrow metrics_prefixes",
                        MAX_METRIC_SAMPLES,
                    )
                    break
            count += emitted
        except Exception as exc:
            logger.warning("Metrics scrape failed: %s", exc)

    return count


def _process_inventory(
    logger,
    models,
    api,
    state,
    checkpoint,
    ckpt_key,
    base_url,
    index,
    source,
    event_writer,
    now_iso,
) -> int:
    count = 0
    current_ids = sorted(m["model_id"] for m in models)
    known_ids = state.get("known_model_ids")

    # Audit events for inventory changes (every cycle, cheap set diff).
    if known_ids is not None:
        added = [m for m in current_ids if m not in set(known_ids)]
        removed = [m for m in known_ids if m not in set(current_ids)]
        for model_id, action in [(m, "model_added") for m in added] + [
            (m, "model_removed") for m in removed
        ]:
            payload = envelope(
                {
                    "model_id": model_id,
                    "server_type": api.server_type,
                    "model_count": len(current_ids),
                    "base_url": base_url,
                },
                provider=PROVIDER_SELFHOSTED,
                category="audit",
                action=action,
            )
            write_json_event(
                event_writer=event_writer,
                payload=payload,
                index=index,
                sourcetype=ST_SELFHOSTED_AUDIT,
                source=source,
                event_time=now_iso,
            )
            count += 1
        if added or removed:
            logger.info("Model inventory changed: +%s -%s", len(added), len(removed))

    # Full snapshot at most every 12 hours (or when inventory changed).
    last_snapshot = float(state.get("last_model_snapshot") or 0)
    inventory_changed = known_ids is not None and set(known_ids) != set(current_ids)
    if (
        known_ids is None
        or inventory_changed
        or time.time() - last_snapshot >= MODEL_SNAPSHOT_SECONDS
    ):
        for model in models:
            payload = envelope(
                dict(
                    model,
                    snapshot_time=now_iso,
                    server_type=api.server_type,
                    base_url=base_url,
                ),
                provider=PROVIDER_SELFHOSTED,
                category="directory",
                action="model_snapshot",
            )
            write_json_event(
                event_writer=event_writer,
                payload=payload,
                index=index,
                sourcetype=ST_SELFHOSTED_MODEL,
                source=source,
                event_time=now_iso,
            )
            count += 1
        checkpoint.update(
            ckpt_key,
            known_model_ids=current_ids,
            last_model_snapshot=time.time(),
        )
    else:
        checkpoint.update(ckpt_key, known_model_ids=current_ids)

    return count
