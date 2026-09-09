"""Anthropic requests must authenticate with the x-api-key scheme.

Every Anthropic endpoint the add-on calls - the compliance activity feed,
the organization directory, and the analytics summaries / usage_report /
cost_report - accepts an API key only through the ``x-api-key`` header;
``Authorization: Bearer`` is reserved for OAuth tokens, which the add-on
does not use. The analytics client once sent ``Authorization: Bearer
<key>``, so every analytics request failed authentication. These checks
pin the scheme both on the header builders and on the requests they
actually produce.

Runs two ways, mirroring test_version_sync.py, so it needs no third-party
imports:

    pytest tests/
    python3 tests/test_anthropic_api_headers.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _anthropic():
    """Import the provider client with the add-on's bin/ on sys.path."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "package", "bin"))
    try:
        from ai_governance import ANTHROPIC_VERSION
        from ai_governance.providers.anthropic_api import AnthropicAPI
    finally:
        sys.path.pop(0)
    return ANTHROPIC_VERSION, AnthropicAPI


class _RecordingClient:
    """Stands in for JsonHttpClient; records requests, returns empty pages."""

    def __init__(self):
        self.calls = []

    def get_json(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return {"data": []}


def test_admin_headers_use_x_api_key():
    anthropic_version, anthropic_api = _anthropic()
    api = anthropic_api("admin-key", analytics_key="analytics-key")
    assert api._admin_headers() == {
        "x-api-key": "admin-key",
        "anthropic-version": anthropic_version,
    }


def test_analytics_headers_use_x_api_key():
    anthropic_version, anthropic_api = _anthropic()
    api = anthropic_api("admin-key", analytics_key="analytics-key")
    headers = api._analytics_headers()
    assert headers == {
        "x-api-key": "analytics-key",
        "anthropic-version": anthropic_version,
    }
    # The regression this file exists for: an API key sent as a Bearer
    # token is rejected by the analytics endpoints.
    assert "Authorization" not in headers


def test_analytics_key_falls_back_to_admin_key():
    _, anthropic_api = _anthropic()
    api = anthropic_api("admin-key")
    assert api._analytics_headers()["x-api-key"] == "admin-key"


def test_analytics_requests_carry_analytics_headers():
    anthropic_version, anthropic_api = _anthropic()
    api = anthropic_api("admin-key", analytics_key="analytics-key")
    client = _RecordingClient()
    api._client = client
    list(api.analytics_summaries("2026-08-16", "2026-08-17"))
    list(api.analytics_usage("2026-08-16", "2026-08-17"))
    list(api.analytics_cost("2026-08-16", "2026-08-17"))
    assert len(client.calls) == 3
    for call in client.calls:
        assert call["headers"] == {
            "x-api-key": "analytics-key",
            "anthropic-version": anthropic_version,
        }


def test_compliance_requests_carry_admin_headers():
    anthropic_version, anthropic_api = _anthropic()
    api = anthropic_api("admin-key", analytics_key="analytics-key")
    client = _RecordingClient()
    api._client = client
    list(api.list_activities(max_items=1))
    list(api.list_users(max_items=1))
    assert len(client.calls) == 2
    for call in client.calls:
        assert call["headers"] == {
            "x-api-key": "admin-key",
            "anthropic-version": anthropic_version,
        }


CHECKS = (
    test_admin_headers_use_x_api_key,
    test_analytics_headers_use_x_api_key,
    test_analytics_key_falls_back_to_admin_key,
    test_analytics_requests_carry_analytics_headers,
    test_compliance_requests_carry_admin_headers,
)


def _main():
    failures = 0
    for check in CHECKS:
        try:
            check()
        except AssertionError as exc:
            print(f"{check.__name__}: {exc}", file=sys.stderr)
            failures += 1
    if failures:
        return 1
    print(f"anthropic header scheme OK: {len(CHECKS)} checks")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
