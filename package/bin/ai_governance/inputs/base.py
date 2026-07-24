"""Common driver for all modular inputs in this add-on."""

from __future__ import annotations

from typing import Callable

from solnlib import log
from splunklib import modularinput as smi

from ai_governance.input_utils import configure_logger, logger_for_input


def run_input(
    inputs: smi.InputDefinition,
    event_writer: smi.EventWriter,
    input_type: str,
    collect: Callable[..., int],
    sourcetype: str,
) -> None:
    """Iterate configured input stanzas, drive collection, log lifecycle."""
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input("%s_%s" % (input_type, normalized_input_name))
        session_key = inputs.metadata["session_key"]
        try:
            configure_logger(logger, session_key)
        except Exception:
            pass  # fall back to default level rather than dropping collection
        log.modular_input_start(logger, normalized_input_name)
        try:
            count = collect(
                logger=logger,
                session_key=session_key,
                input_key=input_name,
                input_item=input_item,
                event_writer=event_writer,
            )
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                count,
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as exc:
            log.log_exception(
                logger,
                exc,
                "%s_error" % input_type,
                msg_before="Failed to collect %s data: " % input_type,
            )


def stanza_key(input_key: str) -> str:
    """Stable checkpoint key for an input stanza (scheme://name)."""
    return input_key.replace("://", ":")
