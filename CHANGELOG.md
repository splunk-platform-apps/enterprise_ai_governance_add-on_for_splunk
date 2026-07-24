
# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).

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
