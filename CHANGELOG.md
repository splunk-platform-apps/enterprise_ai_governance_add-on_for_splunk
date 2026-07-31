
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.0.4] - 2026-07-31

### Fixed

- **Security**: every dashboard filter input is now escaped before it is interpolated into SPL. The **User filter** on *AI Security Audit*, the **Server** selector on *Self-Hosted & Open-Source Models*, and the **Provider** selector on *AI Security Audit*, *AI Governance Overview* and *AI Usage & Cost* previously supplied their own quotes via input `prefix`/`suffix`/`valuePrefix`/`valueSuffix`, so a value containing a double quote could terminate the intended `aigov_user="…"` / `base_url="…"` / `aigov_provider IN ("…")` term and append arbitrary search syntax. The quoting now lives in the queries and goes through the `|s` token filter, which escapes embedded quotes. Filtering behaviour is unchanged for ordinary values, wildcards and multi-provider selections.

## [1.0.3] - 2026-07-27

### Added

- **Documentation** and **Report an issue** links in the app navigation bar, pointing at the published documentation site and the repository issue tracker
- Save-time format validation on the OpenAI Admin API key account field (`sk-admin-` prefix) with guidance naming the org-Owner requirement
- Documentation: OpenAI setup states that only an organization Owner can create an Admin API key; troubleshooting covers the `Missing scopes: api.audit_logs.read` error including a curl test to verify the key outside Splunk

### Fixed

- OpenAI audit input no longer aborts audit-log collection when the optional user-directory snapshot fails (for example on a missing scope); it logs a warning and keeps ingesting audit events
- OpenAI audit input now logs an actionable remediation message on HTTP 401/403, naming the organization Admin API key (`sk-admin-...`) and org-Owner requirement

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
- Five dashboards (Overview, Security Audit, Usage & Cost, Self-Hosted AI, Compliance) and eight ready-to-enable alerts
- KV Store checkpointing (`ta_ai_governance_checkpoints`) and encrypted credential storage via UCC
