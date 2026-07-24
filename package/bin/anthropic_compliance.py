import import_declare_test  # noqa: F401 — sets up sys.path for bundled lib/ (side-effect import)

import sys

from splunklib import modularinput as smi
from anthropic_compliance_helper import stream_events, validate_input


class ANTHROPIC_COMPLIANCE(smi.Script):
    def __init__(self):
        super(ANTHROPIC_COMPLIANCE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("anthropic_compliance")
        scheme.description = "Anthropic Compliance Activity Feed"
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
                "collect_directory",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == "__main__":
    exit_code = ANTHROPIC_COMPLIANCE().run(sys.argv)
    sys.exit(exit_code)
