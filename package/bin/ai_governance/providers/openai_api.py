"""OpenAI organization (platform) API client - audit logs, users, usage, costs."""

from __future__ import annotations

from typing import Any, Dict, Iterator, Optional

from ai_governance import OPENAI_API_BASE
from ai_governance.http_client import JsonHttpClient

MAX_PAGE_SIZE = 100


class OpenAIAPI:
    def __init__(self, admin_key, proxy_url=None):
        self._client = JsonHttpClient(proxy_url=proxy_url)
        self._admin_key = admin_key

    def _headers(self):
        return {"Authorization": "Bearer %s" % self._admin_key}

    def _get(self, path, params=None):
        return self._client.get_json(
            OPENAI_API_BASE + path, headers=self._headers(), params=params
        )

    def paginate(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_items: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Cursor pagination using after / has_more / last_id."""
        query = dict(params or {})
        query.setdefault("limit", min(MAX_PAGE_SIZE, max_items or MAX_PAGE_SIZE))
        collected = 0
        while True:
            response = self._get(path, params=query)
            items = response.get("data", [])
            if not isinstance(items, list):
                return
            for item in items:
                yield item
                collected += 1
                if max_items and collected >= max_items:
                    return
            if not response.get("has_more"):
                return
            last_id = response.get("last_id")
            if not last_id and items:
                last_id = items[-1].get("id")
            if not last_id:
                return
            query["after"] = last_id

    def list_audit_logs(self, effective_at_gt=None, max_items=None):
        params = {}
        if effective_at_gt is not None:
            params["effective_at[gt]"] = int(effective_at_gt)
        return self.paginate(
            "/v1/organization/audit_logs", params=params, max_items=max_items
        )

    def list_users(self, max_items=None):
        return self.paginate("/v1/organization/users", max_items=max_items)

    def _paginate_pages(self, path, params):
        """Usage/costs pagination via next_page token."""
        query = dict(params or {})
        while True:
            response = self._get(path, params=query)
            for bucket in response.get("data", []):
                yield bucket
            next_page = response.get("next_page")
            if not (response.get("has_more") and next_page):
                return
            query["page"] = next_page

    def usage_completions(self, start_time, end_time=None, bucket_width="1d"):
        params = {
            "start_time": int(start_time),
            "bucket_width": bucket_width,
            "group_by": ["model", "project_id"],
            "limit": 30 if bucket_width == "1d" else 168,
        }
        if end_time:
            params["end_time"] = int(end_time)
        return self._paginate_pages("/v1/organization/usage/completions", params)

    def costs(self, start_time, end_time=None):
        params = {
            "start_time": int(start_time),
            "bucket_width": "1d",
            "group_by": ["project_id", "line_item"],
            "limit": 30,
        }
        if end_time:
            params["end_time"] = int(end_time)
        return self._paginate_pages("/v1/organization/costs", params)
