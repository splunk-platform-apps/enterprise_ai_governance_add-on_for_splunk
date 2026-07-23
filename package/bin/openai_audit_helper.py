import import_declare_test  # noqa: F401 isort: skip

from ai_governance.inputs.openai_audit import (
    stream_events as _stream_events,
    validate_input as _validate_input,
)


def validate_input(definition):
    return _validate_input(definition)


def stream_events(inputs, event_writer):
    return _stream_events(inputs, event_writer)
