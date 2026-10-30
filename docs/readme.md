# Enterprise AI Governance Add-on for Splunk

This add-on collects audit, directory, usage, cost, and health data from enterprise AI platforms into Splunk. It supports Anthropic Claude Enterprise, OpenAI (ChatGPT Enterprise / API Platform), Google Gemini (Workspace), Microsoft 365 Copilot, and self-hosted LLM servers.

The add-on handles provider connections, data collection, and normalization. It polls each configured provider's APIs on a schedule, normalizes the responses into `aigov_*` fields and indexes the resulting events.

The [Enterprise AI Governance App for Splunk](https://github.com/splunk-platform-apps/enterprise_ai_governance_app_for_splunk) provides dashboards, search macros, and alerts for the collected data; **install the App separately if you want those features**.

## Features

* Data collection from five provider families, through 19 [sourcetypes](#sourcetypes) and 9 [inputs](#usage), *Anthropic Compliance Activity Feed*, *Anthropic Usage & Cost Analytics*, *OpenAI Compliance Logs (ChatGPT Enterprise)*, *OpenAI Platform Audit Logs*, *OpenAI Usage & Costs*, *Google Gemini Audit (Workspace)*, *Microsoft 365 Copilot Audit*, *Microsoft 365 Copilot Usage* and *Self-Hosted Model Monitor*.
* **Normalized schema** — collected events use shared fields such as `aigov_provider`, `aigov_product`, `aigov_category`, `aigov_action`, `aigov_user`, and `aigov_src_ip`, where applicable.
* **Proxy support** — an optional per-account proxy URL routes provider traffic through your egress proxy.

> [!NOTE]
> OpenAI Platform Audit Logs and OpenAI Compliance Logs answer different questions and need different credentials, so they are separate inputs rather than one input with a toggle. In particular:
> - *OpenAI Platform Audit Logs* reads `api.openai.com` with a platform Admin API key and reports on organization administration.
> - *OpenAI Compliance Logs* reads the ChatGPT Enterprise Compliance Logs Platform on `api.chatgpt.com` with a separate Compliance API key and reports on what users actually did in ChatGPT.

### Sourcetypes

| Provider | Sourcetypes |
|---|---|
| Anthropic | `anthropic:compliance:activity`, `anthropic:compliance:user`, `anthropic:compliance:group`, `anthropic:analytics:usage`, `anthropic:analytics:cost`, `anthropic:analytics:summary` (shared with the [Anthropic Claude Enterprise Add-on](https://github.com/splunk-platform-apps/anthropic_claude_enterprise_add-on_for_splunk)) |
| OpenAI | `aigov:openai:compliance`, `aigov:openai:audit`, `aigov:openai:user`, `aigov:openai:usage`, `aigov:openai:cost` |
| Google | `aigov:gemini:audit` |
| Microsoft | `aigov:copilot:interaction`, `aigov:copilot:usage` |
| Self-hosted | `aigov:selfhosted:model`, `aigov:selfhosted:audit`, `aigov:selfhosted:metric`, `aigov:selfhosted:runtime`, `aigov:selfhosted:health` |

:point_right: `props.conf` also carries extraction stanzas for additional `anthropic:compliance:*` and `anthropic:analytics:*` sourcetypes that belong to the shared Anthropic taxonomy but are not written by this add-on's inputs.

## Getting Started
### Requirements

* Splunk Cloud Platform, or Splunk Enterprise 10.x — standalone (distributed and search head cluster deployments are not yet validated).
* HTTPS egress from the instance running the inputs to the provider APIs you enable, or connectivity to your self-hosted LLM servers.
* Admin-level API credentials with the required permissions for each provider you enable. Self-hosted servers may not require a key. See [below](#provider-permissions-and-scopes) for the required keys, scopes, and permissions.

#### Provider permissions and scopes

Check credential types and permissions carefully: some inputs require an organization or administrator-level key rather than a member-level key.

| Provider | What you need |
|---|---|
| Anthropic Claude Enterprise | An Admin/Compliance API key for the activity feed and users/groups directory. Optionally an Analytics API key with `read:analytics` scope for usage, cost, and adoption data. |
| OpenAI (platform) | An organization Admin API key with `api.audit_logs.read` and usage scopes. Only an organization owner can create one at `platform.openai.com` → **Settings → Organization → Admin keys**. |
| OpenAI (ChatGPT Enterprise compliance) | A Compliance API key and the ChatGPT workspace ID (a UUID) or API Platform organization ID it is scoped to. An organization owner creates the key and OpenAI must approve the Compliance API scopes on it. |
| Google Gemini (Workspace) | An OAuth client ID and client secret plus a refresh token authorized by a Workspace admin for the scope `https://www.googleapis.com/auth/admin.reports.audit.readonly` |
| Microsoft 365 Copilot | An Entra ID app registration (tenant ID, client ID, client secret) with the application permissions `AuditLogsQuery.Read.All` and `Reports.Read.All`, admin-consented. |
| Self-hosted LLM servers | Optionally a static API key. HTTPS with certificate verification is the default. |

### Installation

Download the [latest release](https://github.com/splunk-platform-apps/enterprise_ai_governance_add-on_for_splunk/releases) and install it via **Apps → Manage Apps → Install app from file** (Splunk Enterprise), the self-service app install flow (Splunk Cloud), or [ACS](https://docs.splunk.com/Documentation/SplunkCloud/latest/Config/ManageApps).

Where to install:

| Tier | Install? | Why |
|---|---|---|
| Search head | No | This TA is only for data ingestion and does not include dashboards or search-time configurations. |
| Heavy forwarder / IDM | Yes | Data collection (modular inputs) — enable inputs only here. |
| Indexers | No | This TA only supports modular input-based data collection which uses a heavy forwarder. |
| Universal forwarder | No | Not applicable. |

On a single instance, one installation does everything.

### Configuration

Splunk Admins are requested to:

1. **(Recommended) Create a dedicated index on the Search head** to collect your events, e.g. `ai_governance`.

    1. **Scope the search macro in the Search Head** — if you used a dedicated index, change the `aigov_index` macro from the default `index=*` to e.g. `index=ai_governance` via **Settings → Advanced search → Search macros**. Every dashboard and saved search reads through this macro.

2. **Add an account on the Heavy Forwarder** — open the add-on, go to
   **Configuration → AI Provider Accounts → Add**, pick a provider, and enter its credentials depending on each [provider requirements](#provider-permissions-and-scopes). Add one account per provider, or per org/tenant if you have several. Each account also accepts an optional proxy URL. Provider API keys and secrets are stored using Splunk credential secure storage.

### Usage

1. **Create inputs on the Heavy Forwarder** under **Inputs → Create New Input**:

  | Provider | Input(s) | Data collected |
  |---|---|---|
  | Anthropic Claude Enterprise | *Anthropic Compliance Activity Feed*, *Anthropic Usage & Cost Analytics* | Compliance API activity feed; users and groups directory; usage, cost, and adoption analytics. |
  | OpenAI (ChatGPT Enterprise / API Platform) | *OpenAI Compliance Logs (ChatGPT Enterprise)*, *OpenAI Platform Audit Logs*, *OpenAI Usage & Costs* | ChatGPT Enterprise compliance logs (end-user activity); platform organization audit logs (50+ event types); user directory; aggregated token usage; daily costs. |
  | Google Gemini (Workspace) | *Google Gemini Audit (Workspace)* | Admin SDK Reports API Gemini audit events. |
  | Microsoft 365 Copilot | *Microsoft 365 Copilot Audit*, *Microsoft 365 Copilot Usage*  | Purview audit records; per-user usage reports. |
  | Self-hosted LLM servers (vLLM, Ollama, LiteLLM, any OpenAI-compatible) | *Self-Hosted Model Monitor* | Model inventory, Prometheus metrics, runtime info, health checks. |

  Select the **Account** and set the **Index** on each input to your dedicated index.

  :point_right: Audit inputs backfill 7 days of history on their first run by default.

2. Verify data. Wait one collection interval, then run:

  ```spl
  <!-- Explore AI provider activity across your organization -->
  index=ai_governance | head 20
  <!-- Count events by sourcetype -->
  | tstats count where index=ai_governance by sourcetype
  ```

  Use the `aigov_*` normalized fields to correlate events across providers — for example, by user, action, or timestamp.

> [!WARNING] **Backfills**
> The OpenAI and Gemini audit APIs return newest events first. If the initial backfill window holds more events than `max_events_per_cycle`, the oldest events in that window are skipped (a warning is logged when the cap is reached). Raise `max_events_per_cycle` on the input before its first run if you need a large backfill.

#### Configuring the `OpenAI Compliance Logs` input

Two settings on *OpenAI Compliance Logs (ChatGPT Enterprise)* deserve particular attention:

1. **Event types** — a comma-separated list of Compliance Logs event types, defaulting to `AUTH_LOG`. The set available to your workspace is listed in the Compliance API reference at `chatgpt.com/admin/api-reference`, which requires you to be signed in to your Enterprise or Edu workspace. Add the types you want; an unrecognized type is skipped with a warning and does not stop the others.
2. **Index full message content** — off by default. When off, prompt and response text is replaced with a redaction marker and a character count while message roles, IDs, and timestamps are preserved, and events carry `aigov_content_redacted=true`. Turn it on only once you have confirmed that the target index's retention, access controls, and data classification allow storing conversation content verbatim.

:points_right: The Compliance Logs Platform retains roughly 30 days of history, so the backfill window on this input is capped at 30 days. Continuous collection is important for retaining these records in Splunk.

## Troubleshooting

Each input writes its own log to `$SPLUNK_HOME/var/log/splunk/ta_ai_governance_<input_name>.log`, searchable with:

```spl
index=_internal source=*ta_ai_governance* (ERROR OR WARN*)
```

| Symptom | Check |
|---|---|
| No events at all | Is the input enabled? Are the account credentials valid? Does the index exist and match the input's index setting? |
| `401` / `403` in logs | Check the key type and scopes, or missing admin consent (Microsoft) / admin authorization (Google). |
| OpenAI: `Missing scopes: api.audit_logs.read` | The configured key is not an org **Admin API key**, or was created without the audit-logs scope. Have an **organization owner** create one (`sk-admin-...`) under **Settings → Organization → Admin keys**, then test it outside Splunk: `curl -sS "https://api.openai.com/v1/organization/audit_logs?limit=1" -H "Authorization: Bearer $KEY"` |
| OpenAI Compliance Logs: `401` / `403` | Check that you used a **Compliance API key**, its scopes were approved by OpenAI and the workspace or organization ID matches the key. Test the endpoint outside Splunk using a timestamp within the API retention window. |
| OpenAI Compliance Logs: one event type is skipped with a warning | That event type may not be available to your workspace. Check the list in the Compliance API reference at `chatgpt.com/admin/api-reference` and correct the input **Event types** field; the remaining types keep collecting. |
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

* Built by [Michael Yeack](https://github.com/myeackcisco) and [Manan Grover](https://github.com/manangro).

## References

* [Anthropic Admin & Compliance APIs](https://platform.claude.com/docs/en/api/administration-api)
* [OpenAI Audit Logs API](https://platform.openai.com/docs/api-reference/audit-logs)
* [OpenAI Compliance Platform for Enterprise and Edu customers](https://help.openai.com/en/articles/9261474-openai-compliance-platform-for-enterprise-and-edu-customers)
* [OpenAI Compliance Logs Platform quickstart (Cookbook)](https://cookbook.openai.com/examples/chatgpt/compliance_api/logs_platform)
* [Google Workspace Admin SDK Reports API](https://developers.google.com/workspace/admin/reports/v1/get-start/getting-started)
* [Microsoft Graph audit log query API](https://learn.microsoft.com/en-us/graph/api/resources/security-auditlogquery)

## Contributing

See the [CONTRIBUTING.md](https://github.com/splunk-platform-apps/.github/blob/main/.github/CONTRIBUTING.md) file for details.
