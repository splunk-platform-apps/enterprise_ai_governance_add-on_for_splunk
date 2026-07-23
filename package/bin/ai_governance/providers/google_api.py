"""Google Workspace Admin SDK Reports API client (Gemini audit).

Authenticates with an OAuth 2.0 refresh token (no crypto dependencies
needed) and reads audit activity for Gemini applications via
https://admin.googleapis.com/admin/reports/v1.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional

from ai_governance import GOOGLE_REPORTS_BASE, GOOGLE_TOKEN_URL
from ai_governance.http_client import APIError, JsonHttpClient

MAX_PAGE_SIZE = 1000


class GoogleReportsAPI:
    def __init__(self, client_id, client_secret, refresh_token, proxy_url=None):
        self._client = JsonHttpClient(proxy_url=proxy_url)
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = None
        self._token_expiry = 0.0

    def _token(self):
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token
        response = self._client.post_form(
            GOOGLE_TOKEN_URL,
            {
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            },
        )
        token = response.get("access_token")
        if not token:
            raise APIError(401, "Google token endpoint returned no access_token")
        self._access_token = token
        self._token_expiry = time.time() + float(response.get("expires_in", 3600))
        return token

    def list_activities(
        self,
        application_name: str,
        start_time: Optional[str] = None,
        customer_id: Optional[str] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Iterate audit activity items (ascending is not supported; the API
        returns newest first, so callers checkpoint on max event time)."""
        url = "%s/admin/reports/v1/activity/users/all/applications/%s" % (
            GOOGLE_REPORTS_BASE,
            application_name,
        )
        params = {"maxResults": MAX_PAGE_SIZE}
        if start_time:
            params["startTime"] = start_time
        if customer_id and customer_id != "my_customer":
            params["customerId"] = customer_id
        collected = 0
        while True:
            headers = {"Authorization": "Bearer %s" % self._token()}
            response = self._client.get_json(url, headers=headers, params=params)
            for item in response.get("items", []):
                yield item
                collected += 1
                if max_items and collected >= max_items:
                    return
            next_token = response.get("nextPageToken")
            if not next_token:
                return
            params["pageToken"] = next_token
