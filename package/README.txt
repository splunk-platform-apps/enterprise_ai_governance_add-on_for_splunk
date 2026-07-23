Enterprise AI Governance Add-on for Splunk
===========================================

Version 1.0.2

Collects audit, directory, usage and cost data from enterprise AI platforms
into Splunk for monitoring, governance and security:

  * Anthropic Claude Enterprise  - Compliance API activity feed, users/groups
                                   directory, usage/cost/adoption analytics
  * OpenAI (ChatGPT Enterprise / - Organization audit logs, user directory,
    API Platform)                  aggregated token usage and daily costs
  * Google Gemini (Workspace)    - Admin SDK Reports API Gemini audit events
  * Microsoft 365 Copilot        - Purview audit records (copilotInteraction)
                                   via Microsoft Graph, per-user usage reports

Includes dashboards for governance overview, security audit, usage & cost
monitoring, and compliance/directory posture, plus ready-to-enable alerts.

Supported deployments: Splunk Cloud (vetted-app compatible), Splunk
Enterprise 9.x standalone and distributed (search head clustering supported;
checkpoints are stored in the KV Store).

SETUP
-----
1. Install the add-on on your search head (Splunk Cloud: install via
   Splunkbase / private app upload). For distributed on-prem deployments,
   install on the search head and on the heavy forwarder / IDM that runs the
   inputs.
2. Open the add-on > Configuration > AI Provider Accounts > Add, pick a
   provider and enter credentials:
     - Anthropic: Admin/Compliance API key (sk-ant-admin...), optional
       Analytics key with read:analytics scope.
     - OpenAI: organization Admin API key (sk-admin-...) with
       api.audit_logs.read and usage scopes.
     - Google Gemini: OAuth client ID/secret and a refresh token authorized
       for scope https://www.googleapis.com/auth/admin.reports.audit.readonly
       by a Workspace admin.
     - Microsoft 365 Copilot: Entra app registration (tenant ID, client ID,
       client secret) with application permissions AuditLogsQuery.Read.All
       and Reports.Read.All (admin consent required).
3. Create Inputs for the data you want and point them at an index.
4. Update the `aigov_index` macro (Settings > Advanced search > Search
   macros) to match the index you selected.

All credentials are stored encrypted using Splunk secure storage. All
outbound calls are HTTPS with certificate verification; an optional per-
account proxy URL is supported.

Note on backfills: the OpenAI and Gemini audit APIs return newest events
first. If the initial backfill window holds more events than
max_events_per_cycle, the oldest events in that window are skipped (a
warning is logged when the cap is hit) - raise max_events_per_cycle on the
input before the first run if you need a large backfill.

SOURCETYPES
-----------
anthropic:compliance:activity, anthropic:compliance:user,
anthropic:compliance:group, anthropic:analytics:usage,
anthropic:analytics:cost, anthropic:analytics:summary (shared with the
Anthropic Claude Enterprise Add-on), aigov:openai:audit, aigov:openai:user,
aigov:openai:usage, aigov:openai:cost, aigov:gemini:audit,
aigov:copilot:interaction, aigov:copilot:usage, aigov:selfhosted:model,
aigov:selfhosted:audit, aigov:selfhosted:metric, aigov:selfhosted:runtime,
aigov:selfhosted:health

Every event carries normalized fields: aigov_provider, aigov_product,
aigov_category, aigov_action, aigov_user, aigov_src_ip.

SUPPORT
-------
This add-on is provided as-is under the Apache 2.0 license.
