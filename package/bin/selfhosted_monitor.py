import import_declare_test  # noqa: F401 — sets up sys.path for bundled lib/ (side-effect import)

import sys

from splunklib import modularinput as smi
from selfhosted_monitor_helper import stream_events, validate_input


class SELFHOSTED_MONITOR(smi.Script):
    def __init__(self):
        super(SELFHOSTED_MONITOR, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("selfhosted_monitor")
        scheme.description = "Self-Hosted Model Monitor"
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
                "collect_models",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "collect_metrics",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "metrics_path",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "metrics_prefixes",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "collect_runtime",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == "__main__":
    exit_code = SELFHOSTED_MONITOR().run(sys.argv)
    sys.exit(exit_code)
