"""Cross-provider event normalization.

Every event written by this add-on carries a small common envelope so
dashboards and correlation searches work across providers:

- ``aigov_provider``: anthropic | openai | gemini | microsoft
- ``aigov_product``:  human-readable product name
- ``aigov_category``: audit | directory | usage | cost | summary | interaction
- ``aigov_action``:   provider event/action type when applicable
- ``aigov_user``:     acting user (email / UPN) when applicable
- ``aigov_src_ip``:   source IP when applicable

Compliance Logs records carry two extra fields:

- ``aigov_log_type``: the Compliance Logs Platform ``event_type``
- ``aigov_content_redacted``: true when prompt/response text was stripped
"""

from __future__ import annotations

from typing import Any, Dict, Optional

PRODUCT_NAMES = {
    "anthropic": "Anthropic Claude Enterprise",
    "openai": "OpenAI Platform",
    "gemini": "Google Gemini (Workspace)",
    "microsoft": "Microsoft 365 Copilot",
    "selfhosted": "Self-hosted / Open-source LLM",
}


def envelope(
    payload: Dict[str, Any],
    provider: str,
    category: str,
    action: Optional[str] = None,
    user: Optional[str] = None,
    src_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a shallow copy of payload with the common envelope merged in."""
    event = dict(payload)
    event["aigov_provider"] = provider
    event["aigov_product"] = PRODUCT_NAMES.get(provider, provider)
    event["aigov_category"] = category
    if action:
        event["aigov_action"] = action
    if user:
        event["aigov_user"] = user
    if src_ip:
        event["aigov_src_ip"] = src_ip
    return event


def _first(*values):
    for value in values:
        if value:
            return value
    return None


def normalize_anthropic_activity(activity: Dict[str, Any]) -> Dict[str, Any]:
    actor = activity.get("actor") or {}
    attributes = activity.get("attributes") or {}
    flat = dict(activity)
    if isinstance(actor, dict):
        flat.setdefault("actor_type", actor.get("type"))
        flat.setdefault("actor_email", actor.get("email_address") or actor.get("email"))
        flat.setdefault("actor_user_id", actor.get("id"))
        flat.setdefault("actor_ip_address", actor.get("ip_address"))
    return envelope(
        flat,
        provider="anthropic",
        category="audit",
        action=_first(activity.get("event_type"), activity.get("type")),
        user=flat.get("actor_email"),
        src_ip=_first(flat.get("actor_ip_address"), attributes.get("ip_address")),
    )


def normalize_openai_audit(record: Dict[str, Any]) -> Dict[str, Any]:
    actor = record.get("actor") or {}
    flat = dict(record)
    session = actor.get("session") or {}
    api_key = actor.get("api_key") or {}
    session_user = session.get("user") or {}
    api_key_user = api_key.get("user") or {}
    flat.setdefault("actor_type", actor.get("type"))
    flat.setdefault(
        "actor_email",
        _first(session_user.get("email"), api_key_user.get("email")),
    )
    flat.setdefault("actor_ip_address", session.get("ip_address"))
    return envelope(
        flat,
        provider="openai",
        category="audit",
        action=record.get("type"),
        user=flat.get("actor_email"),
        src_ip=flat.get("actor_ip_address"),
    )


# Keys whose values may carry prompt or response text. Used to strip content
# from Compliance Logs records when an input is configured for metadata only.
_CONTENT_KEYS = frozenset(
    (
        "arguments",
        "attachments",
        "body",
        "completion",
        "content",
        "conversation",
        "input",
        "message",
        "messages",
        "output",
        "parts",
        "prompt",
        "prompts",
        "response",
        "responses",
        "text",
    )
)

_REDACTED = "[redacted by TA-ai-governance]"
_MAX_REDACT_DEPTH = 12


def redact_content(value: Any, _depth: int = 0, _under_content: bool = False) -> Any:
    """Recursively replace prompt/response *text* with a redaction marker.

    Only leaf strings are redacted; containers are walked rather than
    dropped. Replacing a whole ``conversation`` or ``messages`` object would
    also discard its conversation id, message roles and timestamps, which is
    exactly the metadata a governance search needs once the text is gone.

    Redacted strings under a named key keep a ``<key>_chars`` sibling so that
    volume signals (a user pasting 40 KB into a chat) still work without the
    content itself ever reaching the index.
    """
    if _depth >= _MAX_REDACT_DEPTH:
        # Fail closed: an unexpectedly deep structure under a content key is
        # dropped rather than passed through unredacted.
        return _REDACTED if _under_content else value

    if isinstance(value, str):
        # Reached only for bare strings inside a content container, e.g.
        # {"parts": ["some prompt text"]}.
        return _REDACTED if _under_content else value
    if isinstance(value, list):
        return [redact_content(item, _depth + 1, _under_content) for item in value]
    if not isinstance(value, dict):
        return value

    result = {}
    for key, item in value.items():
        is_content = key.lower() in _CONTENT_KEYS
        if is_content and isinstance(item, str):
            result[key] = _REDACTED
            result["%s_chars" % key] = len(item)
        else:
            result[key] = redact_content(item, _depth + 1, is_content)
    return result


def _compliance_category(event_type: Optional[str]) -> str:
    """Map a Compliance Logs event_type onto the shared category taxonomy.

    Matching is by substring rather than a fixed table: the event_type enum
    is workspace-specific and documented only behind the authenticated
    Enterprise API reference, so an unknown type must still land somewhere
    sensible instead of being dropped.
    """
    name = (event_type or "").upper()
    if any(token in name for token in ("CONVERSATION", "MESSAGE", "CHAT", "PROMPT")):
        return "interaction"
    if "USAGE" in name:
        return "usage"
    return "audit"


def normalize_openai_compliance(
    record: Dict[str, Any],
    event_type: str,
    include_content: bool = False,
) -> Dict[str, Any]:
    """Flatten one JSONL record from the Compliance Logs Platform."""
    flat = dict(record)
    actor = record.get("actor") if isinstance(record.get("actor"), dict) else {}
    user = record.get("user") if isinstance(record.get("user"), dict) else {}

    flat.setdefault(
        "actor_email",
        _first(
            record.get("user_email"),
            record.get("email"),
            actor.get("email"),
            user.get("email"),
        ),
    )
    flat.setdefault(
        "actor_user_id",
        _first(record.get("user_id"), actor.get("id"), user.get("id")),
    )
    flat.setdefault(
        "actor_ip_address",
        _first(
            record.get("ip_address"),
            record.get("client_ip"),
            record.get("source_ip"),
            actor.get("ip_address"),
        ),
    )

    if not include_content:
        flat = redact_content(flat)
        flat["aigov_content_redacted"] = True

    # The event_type comes from the request, not the record, so it is always
    # present even when a record carries no type of its own.
    flat["aigov_log_type"] = event_type

    event = envelope(
        flat,
        provider="openai",
        category=_compliance_category(event_type),
        action=_first(
            record.get("event_type"),
            record.get("type"),
            record.get("action"),
            event_type,
        ),
        user=flat.get("actor_email"),
        src_ip=flat.get("actor_ip_address"),
    )
    # Same provider, different product: these records come from ChatGPT
    # Enterprise, not the API platform that aigov:openai:audit reports on.
    # Provider stays "openai" so existing provider-scoped panels still match.
    event["aigov_product"] = "OpenAI ChatGPT Enterprise"
    return event


def compliance_event_time(record: Dict[str, Any]) -> Any:
    """Best-effort event timestamp for a Compliance Logs record."""
    return _first(
        record.get("timestamp"),
        record.get("event_time"),
        record.get("created_at"),
        record.get("time"),
        record.get("end_time"),
    )


def normalize_gemini_activity(item: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten one Admin SDK Reports activity item (one event per sub-event)."""
    flat = dict(item)
    identity = item.get("id") or {}
    actor = item.get("actor") or {}
    flat.setdefault("event_time", identity.get("time"))
    flat.setdefault("application_name", identity.get("applicationName"))
    flat.setdefault("actor_email", actor.get("email"))
    flat.setdefault("actor_profile_id", actor.get("profileId"))
    events = item.get("events") or []
    primary = events[0] if events else {}
    action = primary.get("name")
    return envelope(
        flat,
        provider="gemini",
        category="audit",
        action=action,
        user=flat.get("actor_email"),
        src_ip=item.get("ipAddress"),
    )


def normalize_copilot_record(record: Dict[str, Any]) -> Dict[str, Any]:
    flat = dict(record)
    return envelope(
        flat,
        provider="microsoft",
        category="interaction",
        action=_first(record.get("operation"), record.get("auditLogRecordType")),
        user=_first(record.get("userPrincipalName"), record.get("userId")),
        src_ip=record.get("clientIp"),
    )
