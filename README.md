# Enterprise AI Governance Add-on for Splunk

`TA-ai-governance` collects audit, directory, usage, cost and health data from enterprise AI platforms — Anthropic Claude Enterprise, OpenAI (ChatGPT Enterprise / API Platform), Google Gemini (Workspace), Microsoft 365 Copilot and self-hosted LLM servers — and normalizes every event into one `aigov_*` schema so dashboards, macros and alerts behave the same regardless of which provider produced the event.

The add-on is read-only against provider APIs: every credential it asks for is a read scope, and it does not modify AI provider configuration, users or content. The only non-GET calls it makes are OAuth token requests (Google, Microsoft) and a POST that opens a Microsoft Graph audit-log query job, which is how that API returns Purview records.

## What's in the box

**Nine modular inputs**, one per provider and data domain:

| Provider | Inputs | Data collected |
|---|---|---|
| Anthropic Claude Enterprise | `anthropic_compliance`, `anthropic_analytics` | Compliance API activity feed; users and groups directory; usage, cost and adoption analytics |
| OpenAI (ChatGPT Enterprise / API Platform) | `openai_compliance`, `openai_audit`, `openai_usage` | ChatGPT Enterprise compliance logs (end-user activity); platform organization audit logs; user directory; aggregated token usage; daily costs |
| Google Gemini (Workspace) | `gemini_audit` | Admin SDK Reports API audit events (`gemini_in_workspace_apps`) |
| Microsoft 365 Copilot | `copilot_audit`, `copilot_usage` | Purview audit records (`copilotInteraction`) via Microsoft Graph; per-user usage reports |
| Self-hosted LLM servers (vLLM, Ollama, LiteLLM, any OpenAI-compatible) | `selfhosted_monitor` | Model inventory, Prometheus metrics, runtime info, health checks |

**A normalized schema.** Every event carries `aigov_provider`, `aigov_product`, `aigov_category`, `aigov_action`, `aigov_user` and `aigov_src_ip`. The inputs write 19 sourcetypes (`anthropic:compliance:*`, `anthropic:analytics:*`, `aigov:openai:*`, `aigov:gemini:audit`, `aigov:copilot:*`, `aigov:selfhosted:*`); `props.conf` defines 27, the extras being the Anthropic taxonomy shared with the Anthropic Claude Enterprise Add-on.

**Two OpenAI log planes, deliberately kept separate.** `openai_audit` reads `api.openai.com` with a platform Admin API key and reports on organization administration — keys minted, members invited, projects changed. `openai_compliance` reads the ChatGPT Enterprise Compliance Logs Platform on `api.chatgpt.com` with a separate Compliance API key and reports on what users actually did in ChatGPT. They answer different questions and need different credentials, so they are separate inputs rather than one input with a toggle.

**Five dashboards** — AI Governance Overview (default view), AI Security Audit, AI Usage & Cost Monitoring, Self-Hosted & Open-Source Models, AI Compliance & Directory.

**Eight alerts**, all shipped disabled: API Key Created or Deleted, Admin or SSO Configuration Change, Data Export Activity, New AI User Seen, Off-Hours Activity Spike, Daily Spend Threshold Exceeded, New Self-Hosted Model Detected, Self-Hosted Server Down.

**Eleven search macros** — `aigov_index` (the one macro you must point at your index), the category macros `aigov_all` / `aigov_audit` / `aigov_directory` / `aigov_usage` / `aigov_cost` / `aigov_selfhosted`, and the cross-provider action macros `aigov_signin_actions` / `aigov_admin_actions` / `aigov_key_actions` / `aigov_export_actions`. Plus five event types and CIM-style tags (`authentication`, `change`, `account`, `audit`).

**Operational behavior.** Credentials are stored encrypted in Splunk secure storage; inputs checkpoint to the KV Store collection `ta_ai_governance_checkpoints` so they resume across restarts; audit inputs backfill 7 days on first run by default; each account accepts an optional proxy URL.

**Conversation content is not indexed unless you ask for it.** `openai_compliance` is the one input that can reach actual prompt and response text. Its **Index full message content** option is off by default: content fields are replaced with a redaction marker plus a character count, message roles, ids and timestamps are preserved, and events carry `aigov_content_redacted=true`. Turn it on only once you have confirmed the target index's retention, access controls and data classification allow storing conversation content. Note that the Compliance Logs Platform retains roughly 30 days of history, which is the reason to collect it into Splunk at all.

## Requirements

* Splunk Cloud Platform, or Splunk Enterprise 10.x — standalone. Distributed and search head cluster deployments are designed for but not yet validated.
* HTTPS egress from the instance running the inputs to the provider APIs you enable.
* Admin-level API credentials for at least one provider. Most setup failures are a member-level key used where an admin-level key is required — see the [documentation](https://splunk-platform-apps.github.io/enterprise_ai_governance_add-on_for_splunk/) for the exact key type, scopes and permissions per provider.

## Getting Started

Download the latest compiled add-on from the releases page and install it on the search head; on Splunk Cloud Platform, install it as a private app.

:package: [Download the latest release here](https://github.com/splunk-platform-apps/enterprise_ai_governance_add-on_for_splunk/releases)

Then configure it: create an index, add a provider account under **Configuration → AI Provider Accounts**, create inputs under **Inputs → Create New Input**, and point the `aigov_index` macro at your index. Full step-by-step instructions are in the [documentation](https://splunk-platform-apps.github.io/enterprise_ai_governance_add-on_for_splunk/).

## Repository layout

This repo holds the [UCC framework](https://splunk.github.io/addonfactory-ucc-generator/) *source*, not a built add-on — `ucc-gen build` produces the installable package in CI, and the generated files (`*_rh_*.py`, `import_declare_test.py`, `restmap.conf`, `web.conf`, `server.conf`, `appserver/`, `metadata/`, `VERSION`) are not checked in.

```
globalConfig.json              UCC definition: configuration tabs, account fields, input forms
package/
  app.manifest                 App metadata and version (source of truth for the build)
  bin/
    <input>.py                 Modular input script (scheme + entry point), one per input
    <input>_helper.py          Thin shim delegating to the collector below
    ai_governance/
      inputs/                  The actual collector for each input type
      providers/               Per-provider API clients
      account.py, checkpoint.py, http_client.py, events.py, input_utils.py
  default/                     app.conf, inputs.conf, props.conf, macros.conf,
                               savedsearches.conf, eventtypes.conf, tags.conf, collections.conf
    data/ui/views/             The five dashboards (Simple XML)
    data/ui/nav/               Navigation
  lib/requirements.txt         Python dependencies bundled at build time
  static/                      App icons
docs/readme.md                 Source for the published documentation site
website/                       Docusaurus configuration for that site
```

## Useful Links

:books: [Documentation](https://splunk-platform-apps.github.io/enterprise_ai_governance_add-on_for_splunk/)<br/>
:writing_hand: [Release Notes](./CHANGELOG.md)<br/>
:balance_scale: [License](./LICENSE) (Apache-2.0)

:gear: [Development Guidelines](https://github.com/splunk-platform-apps/.github/blob/main/documentation/DEV_GUIDELINES.md#getting-started)<br/>
:heart_on_fire: [Contributing Guidelines](https://github.com/splunk-platform-apps/.github/blob/main/.github/CONTRIBUTING.md)
