import import_declare_test  # noqa: F401 — sets up sys.path for bundled lib/ (side-effect import)

import sys

from splunklib import modularinput as smi
from openai_usage_helper import stream_events, validate_input


class OPENAI_USAGE(smi.Script):
    def __init__(self):
        super(OPENAI_USAGE, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("openai_usage")
        scheme.description = "OpenAI Usage & Costs"
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
                "lookback_days",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "bucket_width",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "collect_usage",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "collect_costs",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == "__main__":
    exit_code = OPENAI_USAGE().run(sys.argv)
    sys.exit(exit_code)
