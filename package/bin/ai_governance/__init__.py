"""AI Governance Add-on for Splunk - shared constants."""

ADDON_NAME = "TA-ai-governance"
ADDON_VERSION = "1.0.2"  # keep in sync with VERSION / app.conf / app.manifest

SETTINGS_CONF = "ta-ai-governance_settings"
ACCOUNT_CONF = "ta-ai-governance_account"
CHECKPOINT_COLLECTION = "ta_ai_governance_checkpoints"

# Providers
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"
PROVIDER_MICROSOFT = "microsoft"
PROVIDER_SELFHOSTED = "selfhosted"

# Sourcetypes
# Anthropic events use the same sourcetype names as the Anthropic Claude
# Enterprise Add-on (TA-anthropic_claude_enterprise) so both apps share one
# taxonomy and existing data works unchanged.
ST_ANTHROPIC_ACTIVITY = "anthropic:compliance:activity"
ST_ANTHROPIC_USER = "anthropic:compliance:user"
ST_ANTHROPIC_GROUP = "anthropic:compliance:group"
ST_ANTHROPIC_USAGE = "anthropic:analytics:usage"
ST_ANTHROPIC_COST = "anthropic:analytics:cost"
ST_ANTHROPIC_SUMMARY = "anthropic:analytics:summary"

ST_OPENAI_AUDIT = "aigov:openai:audit"
ST_OPENAI_USER = "aigov:openai:user"
ST_OPENAI_USAGE = "aigov:openai:usage"
ST_OPENAI_COST = "aigov:openai:cost"

ST_GEMINI_AUDIT = "aigov:gemini:audit"

ST_COPILOT_INTERACTION = "aigov:copilot:interaction"
ST_COPILOT_USAGE = "aigov:copilot:usage"

ST_SELFHOSTED_MODEL = "aigov:selfhosted:model"
ST_SELFHOSTED_AUDIT = "aigov:selfhosted:audit"
ST_SELFHOSTED_METRIC = "aigov:selfhosted:metric"
ST_SELFHOSTED_RUNTIME = "aigov:selfhosted:runtime"
ST_SELFHOSTED_HEALTH = "aigov:selfhosted:health"

# API base URLs (HTTPS only)
ANTHROPIC_API_BASE = "https://api.anthropic.com"
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_API_BASE = "https://api.openai.com"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REPORTS_BASE = "https://admin.googleapis.com"
MS_LOGIN_BASE = "https://login.microsoftonline.com"
MS_GRAPH_BASE = "https://graph.microsoft.com"
