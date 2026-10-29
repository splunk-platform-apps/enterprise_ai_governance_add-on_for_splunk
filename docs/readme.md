# Enterprise AI Governance Add-on for Splunk

The Enterprise AI Governance Add-on for Splunk (`TA-ai-governance`) collects audit, directory, usage, cost, and health data from enterprise AI platforms into Splunk. It supports Anthropic Claude Enterprise, OpenAI (ChatGPT Enterprise / API Platform), Google Gemini (Workspace), Microsoft 365 Copilot, and self-hosted LLM servers. Configure the inputs to write to a common index to search provider data using a shared `aigov_*` field vocabulary.

The add-on handles provider connections, data collection, and normalization. The Enterprise AI Governance App for Splunk provides dashboards, search macros, and alerts for the collected data; install the App separately if you want those features.

The add-on is built with the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) (`splunk-add-on-ucc-framework` 6.5.x), runs on the Splunk-bundled Python 3 interpreter, and uses `solnlib`, `splunktaucclib`, and the Splunk Python SDK (bundled at build time — nothing to install separately).

Every provider permission the add-on asks for is a read scope: it does not modify your AI provider configuration, your users, or your content. The only non-GET calls it makes are OAuth token requests (Google, Microsoft) and a POST that opens a Microsoft Graph audit-log query job, which is how that API returns Purview records.

## Features

* Data collection from five provider families, with input types for their supported data domains:

  | Provider | Data collected | Inputs |
  |---|---|---|
  | Anthropic Claude Enterprise | Compliance API activity feed; users and groups directory; usage, cost, and adoption analytics | `anthropic_compliance`, `anthropic_analytics` |
  | OpenAI (ChatGPT Enterprise / API Platform) | ChatGPT Enterprise compliance logs (end-user activity); platform organization audit logs (50+ event types); user directory; aggregated token usage; daily costs | `openai_compliance`, `openai_audit`, `openai_usage` |
  | Google Gemini (Workspace) | Admin SDK Reports API Gemini audit events (`gemini_in_workspace_apps`) | `gemini_audit` |
  | Microsoft 365 Copilot | Purview audit records (`copilotInteraction`) via Microsoft Graph; per-user usage reports | `copilot_audit`, `copilot_usage` |
  | Self-hosted LLM servers (vLLM, Ollama, LiteLLM, any OpenAI-compatible) | Model inventory, Prometheus metrics, runtime info, health checks | `selfhosted_monitor` |

* **Normalized schema** — collected events use shared fields such as `aigov_provider`, `aigov_product`, `aigov_category`, `aigov_action`, `aigov_user`, and `aigov_src_ip`, where applicable.
* **KV Store checkpoints** (collection `ta_ai_governance_checkpoints`) — inputs resume where they left off across restarts; checkpoint storage is designed to support search head clustering (not yet validated).
* **Secure credential storage** — provider API keys and secrets are stored using Splunk's credential storage.
* **Proxy support** — an optional per-account proxy URL routes provider traffic through your egress proxy.

## Getting Started

> The add-on polls each configured provider's APIs on a schedule, normalizes the responses into `aigov_*` fields, and indexes the resulting events.

### Requirements

* Splunk Cloud Platform, or Splunk Enterprise 10.x — standalone (distributed and search head cluster deployments are not yet validated).
* HTTPS egress from the instance running the inputs to the provider APIs you enable, or connectivity to your self-hosted LLM servers.
* Credentials with the required permissions for each provider you enable. Self-hosted servers may not require a key. See [Configuration](#configuration) for the required keys, scopes, and permissions.

### Installation

Download the packaged add-on from the [releases page](https://github.com/splunk-platform-apps/enterprise_ai_governance_add-on_for_splunk/releases) and install it following the [Splunk documentation](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons).

**Install this add-on on the search head** for the validated standalone topology; its modular inputs run there.

On Splunk Cloud Platform, install as a private app (self-service app install / ACS).

### Configuration

Setup runs through the add-on's configuration UI — no custom code or scripting.

#### Step 1: Create an index

Create an events index for the data. This guide uses `ai_governance`. To keep provider data together, configure each input to write to this index.

#### Step 2: Gather provider credentials

Check credential types and permissions carefully — some inputs require an organization- or administrator-level key rather than a member-level key.

| Provider | What you need |
|---|---|
| Anthropic Claude Enterprise | An Admin/Compliance API key (`sk-ant-admin...`, sent as `x-api-key`) for the activity feed and users/groups directory; optionally an Analytics key with the `read:analytics` scope (also sent as `x-api-key`) for usage, cost, and adoption data |
| OpenAI (platform) | An organization **Admin API key** (`sk-admin-...`, sent as a `Bearer` token) with `api.audit_logs.read` and usage scopes. Only an organization **Owner** can create one, at platform.openai.com → **Settings → Organization → Admin keys**. Project keys (`sk-proj-...`) and user keys (`sk-...`) cannot read audit logs, and neither can an admin key created without the audit-logs scope |
| OpenAI (ChatGPT Enterprise compliance) | A separate **Compliance API key** (sent as a `Bearer` token to `api.chatgpt.com`), plus the ChatGPT **workspace ID** (a UUID) or API Platform **organization ID** (`org-...`) it is scoped to. An organization **Owner** creates the key and OpenAI must approve the Compliance API scopes on it. Requires ChatGPT Enterprise, Edu, or ChatGPT for Teachers — the platform Admin API key above will not work for this input, and vice versa |
| Google Gemini (Workspace) | An OAuth client ID and client secret plus a refresh token authorized by a Workspace admin for the scope `https://www.googleapis.com/auth/admin.reports.audit.readonly` |
| Microsoft 365 Copilot | An Entra ID app registration (tenant ID, client ID, client secret) with the application permissions `AuditLogsQuery.Read.All` and `Reports.Read.All`, admin-consented |
| Self-hosted LLM servers | Optionally a static API key (`Bearer` token). HTTPS with certificate verification is the default; plain HTTP is an explicit per-account opt-in for lab environments |

#### Step 3: Add provider accounts

Open **Configuration → AI Provider Accounts → Add**, pick a provider, and enter its credentials. Add one account per provider, or per org/tenant if you have several. Each account also accepts an optional proxy URL. Provider secrets are stored using Splunk's credential storage.

#### Step 4: Create inputs

Open **Inputs → Create New Input**, pick the input type (`anthropic_compliance`, `anthropic_analytics`, `openai_compliance`, `openai_audit`, `openai_usage`, `gemini_audit`, `copilot_audit`, `copilot_usage`, or `selfhosted_monitor`), select the account you created, and set **Index** to your index. Audit inputs backfill 7 days of history on their first run by default.

Two settings on **OpenAI Compliance Logs (ChatGPT Enterprise)** deserve particular attention:

* **Event types** — a comma-separated list of Compliance Logs event types, defaulting to `AUTH_LOG`. The set available to your workspace is listed in the Compliance API reference at `chatgpt.com/admin/api-reference`, which requires you to be signed in to your Enterprise or Edu workspace. Add the types you want; an unrecognized type is skipped with a warning and does not stop the others.
* **Index full message content** — off by default. When off, prompt and response text is replaced with a redaction marker and a character count while message roles, IDs, and timestamps are preserved, and events carry `aigov_content_redacted=true`. Turn it on only once you have confirmed that the target index's retention, access controls, and data classification allow storing conversation content verbatim.

The Compliance Logs Platform retains roughly 30 days of history, so the backfill window on this input is capped at 30 days. Continuous collection is important for retaining these records in Splunk.

#### Step 5: Verify data

Wait one collection interval, then run:

```spl
| tstats count where index=ai_governance by sourcetype
```

## Usage

Once data is flowing, search your `ai_governance` index to explore AI provider activity across your organization:

```spl
index=ai_governance | head 20
```

Use the `aigov_*` normalized fields to correlate events across providers — for example, by user, action, or timestamp. Refer to the [Data reference](#data-reference) section below for the complete list of sourcetypes and field mappings.

For dashboards, visualizations, and pre-built searches, install the [Enterprise AI Governance App for Splunk](https://github.com/splunk-platform-apps/enterprise_ai_governance_app_for_splunk).

## Data reference

Sourcetypes written by the add-on:

| Provider | Sourcetypes |
|---|---|
| Anthropic | `anthropic:compliance:activity`, `anthropic:compliance:user`, `anthropic:compliance:group`, `anthropic:analytics:usage`, `anthropic:analytics:cost`, `anthropic:analytics:summary` (shared with the Anthropic Claude Enterprise Add-on) |
| OpenAI | `aigov:openai:compliance`, `aigov:openai:audit`, `aigov:openai:user`, `aigov:openai:usage`, `aigov:openai:cost` |
| Google | `aigov:gemini:audit` |
| Microsoft | `aigov:copilot:interaction`, `aigov:copilot:usage` |
| Self-hosted | `aigov:selfhosted:model`, `aigov:selfhosted:audit`, `aigov:selfhosted:metric`, `aigov:selfhosted:runtime`, `aigov:selfhosted:health` |

`props.conf` also carries extraction stanzas for additional `anthropic:compliance:*` and `anthropic:analytics:*` sourcetypes that belong to the shared Anthropic taxonomy but are not written by this add-on's inputs.

**Backfills:** The OpenAI and Gemini audit APIs return newest events first. If the initial backfill window holds more events than `max_events_per_cycle`, the oldest events in that window are skipped (a warning is logged when the cap is reached). Raise `max_events_per_cycle` on the input before its first run if you need a large backfill.

## Troubleshooting

Each input writes its own log to `$SPLUNK_HOME/var/log/splunk/ta_ai_governance_<input_name>.log`, searchable with:

```spl
index=_internal source=*ta_ai_governance* (ERROR OR WARN*)
```

| Symptom | Check |
|---|---|
| No events at all | Is the input enabled? Are the account credentials valid? Does the index exist and match the input's index setting? |
| `401` / `403` in logs | Check the key type and scopes, or missing admin consent (Microsoft) / admin authorization (Google). |
| OpenAI: `Missing scopes: api.audit_logs.read` | The configured key is not an org **Admin API key**, or was created without the audit-logs scope. Have an organization **Owner** create one (`sk-admin-...`) under **Settings → Organization → Admin keys**, then test it outside Splunk: `curl -sS "https://api.openai.com/v1/organization/audit_logs?limit=1" -H "Authorization: Bearer $KEY"` |
| OpenAI Compliance Logs: `401` / `403` | Check that you used a **Compliance API key**, its scopes were approved by OpenAI, and the workspace or organization ID matches the key. Test the endpoint outside Splunk using a timestamp within the API's retention window. |
| OpenAI Compliance Logs: one event type is skipped with a warning | That event type may not be available to your workspace. Check the list in the Compliance API reference at `chatgpt.com/admin/api-reference` and correct the input's **Event types** field; the remaining types keep collecting. |
| OpenAI Compliance Logs: events arrive without prompt text | Expected when **Index full message content** is off. Events carry `aigov_content_redacted=true`. Enable full content only after confirming that your index retention and access controls allow storing conversation content. |
| Gemini input returns nothing | Reports API events can lag; confirm the refresh token was authorized by a Workspace admin for the audit-readonly scope. |
| Copilot input returns nothing | Check whether Purview auditing is enabled for the tenant and admin consent was granted. Audit records can take a while to appear. |
| Self-hosted input fails to connect | Is the base URL reachable from the Splunk instance? If using HTTP, is the explicit HTTP opt-in enabled? |
| Need more log detail | Under **Configuration → Logging**, set the level to DEBUG and re-check the internal logs. |

Checkpoints live in the KV Store collection `ta_ai_governance_checkpoints`. Deleting an input's checkpoint makes it backfill again from its configured backfill window; expect duplicate events for the overlap.

## Versions Supported

* Splunk Cloud Platform
* Splunk Enterprise 10.x (developed and tested on Splunk Enterprise 10.4, standalone)

## Credits & Acknowledgements

* Built by Michael Yeack and Manan Grover.
* Built with the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) and patterned on the [splunk-example-ta](https://github.com/splunk/splunk-example-ta).

## References

* [Anthropic Admin & Compliance APIs](https://platform.claude.com/docs/en/api/administration-api)
* [OpenAI Audit Logs API](https://platform.openai.com/docs/api-reference/audit-logs)
* [OpenAI Compliance Platform for Enterprise and Edu customers](https://help.openai.com/en/articles/9261474-openai-compliance-platform-for-enterprise-and-edu-customers)
* [OpenAI Compliance Logs Platform quickstart (Cookbook)](https://cookbook.openai.com/examples/chatgpt/compliance_api/logs_platform)
* [Google Workspace Admin SDK Reports API](https://developers.google.com/workspace/admin/reports/v1/get-start/getting-started)
* [Microsoft Graph audit log query API](https://learn.microsoft.com/en-us/graph/api/resources/security-auditlogquery)

## Contributing

See the [CONTRIBUTING.md](https://github.com/splunk-platform-apps/.github/blob/main/.github/CONTRIBUTING.md) file for details. The add-on is built with the [UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/) — refer to its documentation for build and packaging instructions.