"""Microsoft Graph API client (Entra client-credential flow).

Used for:
- Audit Log Query API (security/auditLog/queries) for Copilot interaction
  audit records. Queries are asynchronous server-side: submit, poll, fetch.
- Microsoft 365 Copilot usage reports (reports/getMicrosoft365CopilotUsageUserDetail).
"""

from __future__ import annotations

import time
from typing import Any
from collections.abc import Iterator

from ai_governance import MS_GRAPH_BASE, MS_LOGIN_BASE
from ai_governance.http_client import APIError, JsonHttpClient


class MicrosoftGraphAPI:
    def __init__(self, tenant_id, client_id, client_secret, proxy_url=None):
        self._client = JsonHttpClient(proxy_url=proxy_url)
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._token_expiry = 0.0

    def _token(self):
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token
        response = self._client.post_form(
            f"{MS_LOGIN_BASE}/{self._tenant_id}/oauth2/v2.0/token",
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        token = response.get("access_token")
        if not token:
            raise APIError(401, "Microsoft token endpoint returned no access_token")
        self._access_token = token
        self._token_expiry = time.time() + float(response.get("expires_in", 3600))
        return token

    def _headers(self):
        return {"Authorization": f"Bearer {self._token()}"}

    def _get(self, url, params=None):
        return self._client.get_json(url, headers=self._headers(), params=params)

    # -- Audit Log Query API ---------------------------------------------
    def create_audit_query(
        self,
        display_name: str,
        start_iso: str,
        end_iso: str,
        record_types: list[str],
    ) -> dict[str, Any]:
        body = {
            "displayName": display_name,
            "filterStartDateTime": start_iso,
            "filterEndDateTime": end_iso,
            "recordTypeFilters": record_types,
        }
        return self._client.post_json(
            f"{MS_GRAPH_BASE}/v1.0/security/auditLog/queries",
            headers=self._headers(),
            json_body=body,
        )

    def get_audit_query(self, query_id: str) -> dict[str, Any]:
        return self._get(f"{MS_GRAPH_BASE}/v1.0/security/auditLog/queries/{query_id}")

    def iter_audit_records(
        self, query_id: str, max_items: int | None = None
    ) -> Iterator[dict[str, Any]]:
        url = f"{MS_GRAPH_BASE}/v1.0/security/auditLog/queries/{query_id}/records"
        params: dict[str, Any] | None = {"$top": 500}
        collected = 0
        while url:
            response = self._get(url, params=params)
            params = None  # nextLink already carries query parameters
            for record in response.get("value", []):
                yield record
                collected += 1
                if max_items and collected >= max_items:
                    return
            url = response.get("@odata.nextLink")

    # -- Copilot usage reports ---------------------------------------------
    def copilot_usage_user_detail(self, period: str = "D7") -> list[dict[str, Any]]:
        url = f"{MS_GRAPH_BASE}/v1.0/reports/getMicrosoft365CopilotUsageUserDetail(period='{period}')"
        rows: list[dict[str, Any]] = []
        params: dict[str, Any] | None = {"$format": "application/json"}
        while url:
            response = self._get(url, params=params)
            params = None
            value = response.get("value", [])
            if isinstance(value, list):
                rows.extend(value)
            url = response.get("@odata.nextLink")
        return rows
