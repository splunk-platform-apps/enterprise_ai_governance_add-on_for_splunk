# Enterprise AI Governance Add-on for Splunk

The Enterprise AI Governance Add-on for Splunk (`TA-ai-governance`) collects audit, directory, usage and cost data from enterprise AI platforms into Splunk — one add-on, one normalized schema, provider-agnostic dashboards and alerts. Use Splunk as the control plane for AI governance: security monitoring, compliance auditing, usage and cost visibility, and incident investigation across every LLM platform your organization uses.

The add-on is built with the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) (`splunk-add-on-ucc-framework` 6.5.x), runs on the Splunk-bundled Python 3 interpreter, and uses `solnlib`, `splunktaucclib` and the Splunk Python SDK (bundled at build time — nothing to install separately).

## Features

* Data collection from five provider families, one input type per data domain:

  | Provider | Data collected | Inputs |
  |---|---|---|
  | Anthropic Claude Enterprise | Compliance API activity feed; users and groups directory; usage, cost and adoption analytics | `anthropic_compliance`, `anthropic_analytics` |
  | OpenAI (ChatGPT Enterprise / API Platform) | Organization audit logs (50+ event types); user directory; aggregated token usage; daily costs | `openai_audit`, `openai_usage` |
  | Google Gemini (Workspace) | Admin SDK Reports API Gemini audit events (`gemini_in_workspace_apps`) | `gemini_audit` |
  | Microsoft 365 Copilot | Purview audit records (`copilotInteraction`) via Microsoft Graph; per-user usage reports | `copilot_audit`, `copilot_usage` |
  | Self-hosted LLM servers (vLLM, Ollama, LiteLLM, any OpenAI-compatible) | Model inventory, Prometheus metrics, runtime info, health checks | `selfhosted_monitor` |

* **Normalized schema** — every event carries `aigov_provider`, `aigov_product`, `aigov_category`, `aigov_action`, `aigov_user` and `aigov_src_ip`, so dashboards, macros and alerts work identically across providers.
* **Five dashboards** — AI Governance Overview (default), AI Security Audit, AI Usage & Cost, Self-Hosted AI, and AI Compliance.
* **Eight ready-made alerts** (shipped disabled) — API key lifecycle, admin/SSO changes, data exports, new users, off-hours spikes, spend thresholds, new self-hosted models, server-down.
* **KV Store checkpoints** (collection `ta_ai_governance_checkpoints`) — inputs resume where they left off across restarts; search head clustering is supported.
* **Encrypted credentials** — all API keys and secrets are stored in Splunk secure storage, never in plain-text conf files.
* **Proxy support** — an optional per-account proxy URL routes provider traffic through your egress proxy.

## Getting Started

> The add-on polls each configured provider's admin/audit APIs on a schedule, normalizes the responses into `aigov_*` fields, and indexes them for the bundled dashboards and alerts.

### Requirements

* Splunk Cloud Platform, or Splunk Enterprise 9.x / 10.x — standalone or distributed (search head clustering supported).
* HTTPS egress from the instance running the inputs to the provider APIs you enable (or to your self-hosted LLM servers).
* Admin-level API credentials for at least one supported provider (see [Configuration](#configuration) for the exact keys, scopes and permissions).

### Installation

Download the packaged add-on from the [releases page](https://github.com/splunk-platform-apps/enterprise_ai_governance_add-on_for_splunk/releases) and install it following the [Splunk documentation](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons):

| Deployment | Install on |
|---|---|
| Standalone | The search head — it runs inputs, dashboards and macros |
| Distributed | The search head (dashboards, macros, alerts) **and** the heavy forwarder / IDM that runs the inputs |
| Search head cluster | All SHC members via the deployer; run inputs on a heavy forwarder / IDM, not on the cluster |

On Splunk Cloud, install as a private app (self-service app install / ACS).

### Configuration

The add-on integrates with third-party services. Authentication methods used per provider:

* **Anthropic Claude Enterprise** — API key authentication. An Admin/Compliance API key (`sk-ant-admin...`, sent as `x-api-key`) drives the activity feed and users/groups directory; an optional Analytics key with the `read:analytics` scope (sent as a `Bearer` token) enables usage, cost and adoption data.
* **OpenAI** — API key authentication. An organization Admin API key (`sk-admin-...`, sent as a `Bearer` token) with `api.audit_logs.read` and usage scopes, created under organization settings.
* **Google Gemini (Workspace)** — OAuth 2.0 with a refresh token. Provide an OAuth client ID and client secret plus a refresh token authorized by a Workspace admin for the scope `https://www.googleapis.com/auth/admin.reports.audit.readonly`.
* **Microsoft 365 Copilot** — OAuth 2.0 client-credentials flow against Microsoft Entra ID. Provide tenant ID, client ID and client secret for an app registration with application permissions `AuditLogsQuery.Read.All` and `Reports.Read.All` (admin consent required).
* **Self-hosted LLM servers** — optional static API key (`Bearer` token). HTTPS with certificate verification is the default; plain HTTP is an explicit per-account opt-in for lab environments.

All secrets are stored encrypted in Splunk secure storage. To configure:

1. Create an events index for the data (this guide uses `ai_governance`).
2. In the app, open **Configuration → AI Provider Accounts → Add**, pick a provider and enter its credentials. Add one account per provider (or per org/tenant). Each account also accepts an optional proxy URL.
3. Open **Inputs → Create New Input**, pick the input type, select the account, and set **Index** to your index. Audit inputs backfill 7 days of history on first run by default.
4. Point the `aigov_index` search macro at your index: **Settings → Advanced search → Search macros** (app context `TA-ai-governance`) → edit `aigov_index` → set the definition to `index=ai_governance`. Every dashboard, macro and alert builds on this one macro.

Logging verbosity can be changed under **Configuration → Logging**.

### Usage

Wait one collection interval, then verify data is flowing:

```
| tstats count where index=ai_governance by sourcetype
```

Or, once the `aigov_index` macro is set:

```
`aigov_all` | stats count by aigov_provider, sourcetype
```

Then explore the dashboards from the app navigation bar — **AI Governance Overview** (default view), **AI Security Audit**, **AI Usage & Cost**, **Self-Hosted AI** and **AI Compliance** — and enable the alerts you want under **Settings → Searches, reports, and alerts** (app context `TA-ai-governance`), tuning thresholds to your environment.

Category macros (`aigov_all`, `aigov_audit`, `aigov_directory`, `aigov_usage`, `aigov_cost`, `aigov_selfhosted`) and cross-provider action macros (`aigov_signin_actions`, `aigov_admin_actions`, `aigov_key_actions`, `aigov_export_actions`) are available for your own searches, along with event types for tagging and correlation.

## Data reference

Sourcetypes written by the add-on:

| Provider | Sourcetypes |
|---|---|
| Anthropic | `anthropic:compliance:activity`, `anthropic:compliance:user`, `anthropic:compliance:group`, `anthropic:analytics:usage`, `anthropic:analytics:cost`, `anthropic:analytics:summary` (shared with the Anthropic Claude Enterprise Add-on) |
| OpenAI | `aigov:openai:audit`, `aigov:openai:user`, `aigov:openai:usage`, `aigov:openai:cost` |
| Google | `aigov:gemini:audit` |
| Microsoft | `aigov:copilot:interaction`, `aigov:copilot:usage` |
| Self-hosted | `aigov:selfhosted:model`, `aigov:selfhosted:audit`, `aigov:selfhosted:metric`, `aigov:selfhosted:runtime`, `aigov:selfhosted:health` |

A note on backfills: the OpenAI and Gemini audit APIs return newest events first. If the initial backfill window holds more events than `max_events_per_cycle`, the oldest events in that window are skipped (a warning is logged when the cap is hit) — raise `max_events_per_cycle` on the input before its first run if you need a large backfill.

## Troubleshooting

Each input writes its own log to `$SPLUNK_HOME/var/log/splunk/ta_ai_governance_<input_name>.log`, searchable with:

```
index=_internal source=*ta_ai_governance* (ERROR OR WARN*)
```

| Symptom | Check |
|---|---|
| No events at all | Input enabled? Account credentials valid? Index exists and matches the input's index setting? |
| `401` / `403` in logs | Key type and scopes — most failures are a member key where an admin key is required, or missing admin consent (Microsoft) / admin authorization (Google) |
| Dashboards empty but data is in the index | The `aigov_index` macro still points at its default — set it to your index |
| Gemini input returns nothing | Reports API events can lag; confirm the refresh token was authorized by a Workspace admin for the audit-readonly scope |
| Copilot input returns nothing | Purview auditing enabled for the tenant? Admin consent granted? Audit records can take a while to appear |
| Self-hosted input fails to connect | Base URL reachable from the Splunk instance? Using HTTP without the explicit HTTP opt-in? |
| Need more log detail | **Configuration → Logging** → set level to DEBUG and re-check the internal logs |

Checkpoints live in the KV Store collection `ta_ai_governance_checkpoints`. Deleting an input's checkpoint makes it backfill again from its configured backfill window (expect duplicate events for the overlap).

## Versions Supported

* Splunk Cloud Platform
* Splunk Enterprise 9.x and 10.x (developed and tested on Splunk Enterprise 10.4)

## Credits & Acknowledgements

* Built by the AI Governance Add-on contributors.
* Built with the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) and patterned on the [splunk-example-ta](https://github.com/splunk/splunk-example-ta).

## References

* [Anthropic Admin & Compliance APIs](https://platform.claude.com/docs/en/api/administration-api)
* [OpenAI Audit Logs API](https://platform.openai.com/docs/api-reference/audit-logs)
* [Google Workspace Admin SDK Reports API](https://developers.google.com/workspace/admin/reports/v1/get-start/getting-started)
* [Microsoft Graph audit log query API](https://learn.microsoft.com/en-us/graph/api/resources/security-auditlogquery)

## Contributing

See the [CONTRIBUTING.md](https://github.com/splunk-platform-apps/.github/blob/main/.github/CONTRIBUTING.md) file for details.

### Build and package from source

The repository holds the UCC source (`globalConfig.json` + `package/`). To build locally:

```
pip install -r requirements-dev.txt
ucc-gen build --ta-version 1.0.2
ucc-gen package --path output/TA-ai-governance
```

CI builds, runs Splunk AppInspect and packages the add-on automatically on every pull request, and publishes a release on version tags.
