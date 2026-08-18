[anthropic_compliance://<name>]
account = Select an account with provider Anthropic.
backfill_days = Days of history to collect on first run (max 180). (Default: 7)
collect_directory = Also snapshot organization users and groups each cycle (at most once per 12 hours). (Default: true)
index = (Default: default)
interval = Polling interval in seconds. (Default: 300)
max_events_per_cycle = (Default: 2000)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[anthropic_analytics://<name>]
account = Select an account with provider Anthropic.
collect_cost = (Default: true)
collect_summaries = (Default: true)
collect_usage = (Default: true)
index = (Default: default)
interval = Polling interval in seconds. Analytics data is finalized daily. (Default: 86400)
lookback_days = Re-collect this many trailing days each cycle to pick up late-arriving data. (Default: 7)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[openai_compliance://<name>]
account = Select an account with provider OpenAI that has a Compliance API key and workspace/organization ID configured.
backfill_days = Days of history to collect on first run. The Compliance Logs Platform retains about 30 days, so larger values are capped at 30. (Default: 7)
event_types = Comma-separated Compliance Logs event types to collect, for example AUTH_LOG. The set available to your workspace is listed in the Compliance API reference at chatgpt.com/admin/api-reference. Unrecognized types are skipped with a warning and do not stop the other types. (Default: AUTH_LOG)
include_message_content = Off by default. When enabled, user prompts and model responses are indexed verbatim. Confirm your index retention, access controls and data classification allow storing conversation content before turning this on. When off, content fields are replaced with a redaction marker and a character count, and events carry aigov_content_redacted=true.
index = (Default: default)
interval = Polling interval in seconds. (Default: 300)
max_files_per_cycle = Upper bound on log files downloaded per event type per interval. When the limit is hit the checkpoint stays on the partial page and collection resumes there next interval. (Default: 200)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[openai_audit://<name>]
account = Select an account with provider OpenAI.
backfill_days = Days of history to collect on first run. (Default: 7)
collect_users = Also snapshot organization users each cycle (at most once per 12 hours). (Default: true)
index = (Default: default)
interval = Polling interval in seconds. (Default: 300)
max_events_per_cycle = (Default: 2000)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[openai_usage://<name>]
account = Select an account with provider OpenAI.
bucket_width = (Default: 1d)
collect_costs = (Default: true)
collect_usage = (Default: true)
index = (Default: default)
interval = (Default: 86400)
lookback_days = Re-collect this many trailing days each cycle to pick up late-arriving data. (Default: 7)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[gemini_audit://<name>]
account = Select an account with provider Google Gemini.
applications = Comma-separated Admin SDK Reports applicationName values to collect. (Default: gemini_in_workspace_apps)
backfill_days = Days of history to collect on first run (Reports API retains up to 180 days). (Default: 7)
index = (Default: default)
interval = (Default: 600)
max_events_per_cycle = (Default: 5000)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[copilot_audit://<name>]
account = Select an account with provider Microsoft 365 Copilot.
backfill_days = (Default: 7)
index = (Default: default)
interval = Audit log queries are asynchronous on the Microsoft side; each cycle either submits a new query or retrieves finished results. (Default: 900)
record_types = Comma-separated Microsoft Purview audit record types to collect. (Default: copilotInteraction)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[copilot_usage://<name>]
account = Select an account with provider Microsoft 365 Copilot.
index = (Default: default)
interval = (Default: 86400)
period = (Default: D7)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[selfhosted_monitor://<name>]
account = Select an account with provider Self-hosted / Open-source.
collect_metrics = Scrape the metrics endpoint (vLLM / LiteLLM). Ignored for server types without Prometheus metrics. (Default: true)
collect_models = Snapshot served models each cycle and emit model_added / model_removed audit events on changes. (Default: true)
collect_runtime = For Ollama servers, also collect currently loaded/running models (/api/ps). (Default: true)
index = (Default: default)
interval = Polling interval in seconds. (Default: 300)
metrics_path = (Default: /metrics)
metrics_prefixes = Comma-separated prefixes of Prometheus metric families to ingest. (Default: vllm:,litellm_,ollama_)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[anthropic_compliance]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
backfill_days =
max_events_per_cycle =
collect_directory =

[anthropic_analytics]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
lookback_days =
collect_usage =
collect_cost =
collect_summaries =

[openai_compliance]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
event_types =
backfill_days =
max_files_per_cycle =
include_message_content =

[openai_audit]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
backfill_days =
max_events_per_cycle =
collect_users =

[openai_usage]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
lookback_days =
bucket_width =
collect_usage =
collect_costs =

[gemini_audit]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
backfill_days =
max_events_per_cycle =
applications =

[copilot_audit]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
backfill_days =
record_types =

[copilot_usage]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
period =

[selfhosted_monitor]
* Scheme-level defaults inherited by every configured input of this type.
python.version =
interval =
index =
collect_models =
collect_metrics =
metrics_path =
metrics_prefixes =
collect_runtime =
