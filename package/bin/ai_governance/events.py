"""Cross-provider event normalization.

Every event written by this add-on carries a small common envelope so
dashboards and correlation searches work across providers:

- ``aigov_provider``: anthropic | openai | gemini | microsoft
- ``aigov_product``:  human-readable product name
- ``aigov_category``: audit | directory | usage | cost | summary | interaction
- ``aigov_action``:   provider event/action type when applicable
- ``aigov_user``:     acting user (email / UPN) when applicable
- ``aigov_src_ip``:   source IP when applicable
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
