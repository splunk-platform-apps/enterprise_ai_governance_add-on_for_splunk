"""AI Governance Add-on for Splunk - shared constants."""

import json
import os
import re

ADDON_NAME = "TA-ai-governance"

# Only reached when app.manifest cannot be read; tests/test_version_sync.py
# keeps it level with the manifest, globalConfig.json, app.conf and CHANGELOG.
_FALLBACK_VERSION = "1.0.3"

# Deliberately narrow - this value goes out in an HTTP header.
_VERSION_RE = re.compile(r"^[0-9A-Za-z.+-]{1,32}$")


def _manifest_version():
    """Return the add-on version recorded in app.manifest.

    app.manifest is the version the package is actually stamped with: org CI
    reads ``info.id.version`` from it and passes that to ``ucc-gen build
    --ta-version``. Reading it here keeps the User-Agent honest rather than
    relying on a constant somebody has to remember to bump.

    The manifest sits two directories above this package, in the source tree
    (``package/app.manifest``) and in an installed add-on
    (``$SPLUNK_HOME/etc/apps/TA-ai-governance/app.manifest``) alike. Standard
    library only, for the Splunk-bundled interpreter, and every failure falls
    back to the constant above - reporting a stale version is survivable, an
    input that will not start is not.
    """
    module_dir = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.dirname(os.path.dirname(module_dir))
    manifest_path = os.path.join(app_root, "app.manifest")
    try:
        with open(manifest_path, encoding="utf-8") as manifest_file:
            version = json.load(manifest_file)["info"]["id"]["version"]
    except (OSError, ValueError, KeyError, TypeError):
        return _FALLBACK_VERSION
    if isinstance(version, str) and _VERSION_RE.match(version):
        return version
    return _FALLBACK_VERSION


ADDON_VERSION = _manifest_version()

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
