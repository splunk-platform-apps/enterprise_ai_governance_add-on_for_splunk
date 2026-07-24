import import_declare_test  # noqa: F401 — sets up sys.path for bundled lib/ (side-effect import)

import sys

from splunklib import modularinput as smi
from openai_audit_helper import stream_events, validate_input


class OPENAI_AUDIT(smi.Script):
    def __init__(self):
        super(OPENAI_AUDIT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("openai_audit")
        scheme.description = "OpenAI Audit Logs"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "backfill_days",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "max_events_per_cycle",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "collect_users",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == "__main__":
    exit_code = OPENAI_AUDIT().run(sys.argv)
    sys.exit(exit_code)
