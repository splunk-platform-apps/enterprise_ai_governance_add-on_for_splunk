
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.1.1] - 2026-08-18

### Added

- **User filter** on the *AI Usage & Cost* dashboard. The cost, token, per-model and line-item panels filter on `aigov_user`; the two Microsoft 365 Copilot panels filter on `userPrincipalName`, the field the Copilot usage report identifies users by. Defaults to `*` and is interpolated through the `|s` token filter like the other dashboard inputs

### Fixed

- The **Provider** multiselect on *AI Governance Overview*, *AI Security Audit* and *AI Usage & Cost* returned zero events whenever more than one provider was selected: the `|s` escaping introduced in 1.0.4 quoted the comma-joined selection as a single literal string (`aigov_provider IN ("anthropic,openai")`), which matches no event. All 25 affected panel searches now expand the selection inside a `makeresults` subsearch — `split` on the delimiter, an allowlist `replace`, then `format` — so each value is quoted individually. The 1.0.4 injection-safety guarantee is preserved: the token still passes through `|s`, and the allowlist strips every character outside `[A-Za-z0-9_*,-]` before the value can reach the generated search string

## [1.1.0] - 2026-08-12

### Added

- New `openai_compliance` modular input collecting ChatGPT Enterprise compliance logs from the OpenAI Compliance Logs Platform (`api.chatgpt.com`), covering end-user activity that the platform audit log does not report
- **OpenAI Compliance API key** and **OpenAI workspace / organization ID** account fields, separate from the platform Admin API key because the Compliance API uses a different credential, host and entitlement
- New `aigov:openai:compliance` sourcetype, included in the `aigov_audit` macro; its records carry `aigov_log_type` and `aigov_content_redacted`
- Three panels on the AI Compliance & Directory dashboard: ChatGPT Enterprise Compliance Logs by Type, Compliance Records With Content Redacted, Most Active ChatGPT Enterprise Users
- Documentation: Compliance API credential requirements, event-type configuration, content-redaction behavior, and troubleshooting for compliance-input auth failures and skipped event types

### Changed

- Renamed the `openai_audit` input label to **OpenAI Platform Audit Logs** so the two OpenAI log sources are distinguishable in the Create New Input menu; the input name and existing configurations are unchanged
- Compliance log message content is redacted by default — prompt and response text is replaced with a marker and a character count, preserving message roles, ids and timestamps, unless **Index full message content** is enabled on the input

### Fixed

- Provider credentials are no longer forwarded across a cross-host HTTP redirect; the compliance log download redirects to signed object storage, so `Authorization` and `x-api-key` headers are now stripped when the redirect target host differs. Applies to every provider client, not just the new input

## [1.0.4] - 2026-07-31

### Fixed

- Anthropic Analytics input now derives its collection window from the current UTC date instead of the search head's local date. On a Splunk instance running ahead of UTC, the local "yesterday" could still be the current day in UTC, so the input ingested a partial day, advanced its checkpoint past it and never backfilled it — permanently undercounting usage and cost totals for that day. Instances at or behind UTC were unaffected apart from collecting slightly later in the day.
- **Security**: every dashboard filter input is now escaped before it is interpolated into SPL. The **User filter** on *AI Security Audit*, the **Server** selector on *Self-Hosted & Open-Source Models*, and the **Provider** selector on *AI Security Audit*, *AI Governance Overview* and *AI Usage & Cost* previously supplied their own quotes via input `prefix`/`suffix`/`valuePrefix`/`valueSuffix`, so a value containing a double quote could terminate the intended `aigov_user="…"` / `base_url="…"` / `aigov_provider IN ("…")` term and append arbitrary search syntax. The quoting now lives in the queries and goes through the `|s` token filter, which escapes embedded quotes. Filtering behaviour is unchanged for ordinary values, wildcards and multi-provider selections.

## [1.0.3] - 2026-07-27

### Added

- **Documentation** and **Report an issue** links in the app navigation bar, pointing at the published documentation site and the repository issue tracker
- Save-time format validation on the OpenAI Admin API key account field (`sk-admin-` prefix) with guidance naming the org-Owner requirement
- Documentation: OpenAI setup states that only an organization Owner can create an Admin API key; troubleshooting covers the `Missing scopes: api.audit_logs.read` error including a curl test to verify the key outside Splunk

### Changed

- App label is now **Enterprise AI Governance Add-on for Splunk** in `app.conf`, `app.manifest` and `globalConfig.json` (previously "App for Splunk"), so the navigation title matches the "Add-on" name used everywhere else in the product and documentation

### Fixed

- OpenAI audit input no longer aborts audit-log collection when the optional user-directory snapshot fails (for example on a missing scope); it logs a warning and keeps ingesting audit events
- OpenAI audit input now logs an actionable remediation message on HTTP 401/403, naming the organization Admin API key (`sk-admin-...`) and org-Owner requirement
- Outbound requests to the Anthropic, OpenAI, Google and Microsoft APIs now report the add-on's real version in the `User-Agent` header; it was pinned at `1.0.2` while the rest of the add-on had moved on
- Dashboard names in the 1.0.1 entry below corrected to the labels the dashboards actually ship with

## [1.0.2] - 2026-07-21

### Fixed

- Corrected the Anthropic Analytics API paths to `usage_report` and `cost_report` (the previously used `/analytics/usage` and `/analytics/cost` endpoints do not exist)
- Assorted collector fixes across provider inputs

### Changed

- Repackaged the add-on; superseded single-provider artifacts dropped from the distribution

## [1.0.1] - 2026-07-21

### Added

- Initial multi-provider release of the AI Governance Add-on for Splunk (`TA-ai-governance`), superseding the earlier single-provider Anthropic Claude Enterprise add-on
- Modular inputs for Anthropic Claude Enterprise (compliance activity feed, directory, analytics), OpenAI (organization audit logs, usage and costs), Google Gemini Workspace (Admin SDK Reports audit events), Microsoft 365 Copilot (Purview audit records, usage reports) and self-hosted LLM servers (vLLM, Ollama, LiteLLM, OpenAI-compatible)
- Normalized `aigov_*` event schema, `aigov_index` macro family, event types and tags
- Five dashboards (AI Governance Overview, AI Security Audit, AI Usage & Cost Monitoring, Self-Hosted & Open-Source Models, AI Compliance & Directory) and eight ready-to-enable alerts
- KV Store checkpointing (`ta_ai_governance_checkpoints`) and encrypted credential storage via UCC
