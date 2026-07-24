"""Shared modular input utilities."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from solnlib import conf_manager, log
from splunklib import modularinput as smi

from ai_governance import ADDON_NAME, SETTINGS_CONF


def logger_for_input(input_name: str) -> logging.Logger:
    sanitized = input_name.replace("://", "_").replace("/", "_")
    return log.Logs().get_logger("ta_ai_governance_%s" % sanitized)


def configure_logger(logger: logging.Logger, session_key: str) -> None:
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=ADDON_NAME,
        conf_name=SETTINGS_CONF,
    )
    logger.setLevel(log_level)


def parse_event_time(value: Any) -> Optional[float]:
    """Parse ISO-8601 strings or epoch numbers into an epoch float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if text.replace(".", "", 1).isdigit():
        try:
            return float(text)
        except ValueError:
            return None
    normalized = text.replace("Z", "+00:00")
    # Trim sub-second precision beyond microseconds (Graph emits 7 digits).
    if "." in normalized:
        head, _, tail = normalized.partition(".")
        digits = ""
        offset = ""
        for index, char in enumerate(tail):
            if char.isdigit():
                digits += char
            else:
                offset = tail[index:]
                break
        normalized = head + "." + (digits[:6] or "0") + offset
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def write_json_event(
    event_writer: smi.EventWriter,
    payload: Dict[str, Any],
    index: Optional[str],
    sourcetype: str,
    source: str,
    event_time: Any = None,
) -> None:
    event = smi.Event(
        data=json.dumps(payload, ensure_ascii=False, default=str),
        index=index,
        sourcetype=sourcetype,
        source=source,
        time=parse_event_time(event_time),
    )
    event_writer.write_event(event)


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def parse_csv(value: Any, default=None):
    if not value:
        return list(default or [])
    return [item.strip() for item in str(value).split(",") if item.strip()]
