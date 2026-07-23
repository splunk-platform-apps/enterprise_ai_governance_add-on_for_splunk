"""Anthropic Compliance / Admin / Analytics API client."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Iterator, Optional

from ai_governance import ANTHROPIC_API_BASE, ANTHROPIC_VERSION
from ai_governance.http_client import JsonHttpClient

MAX_PAGE_SIZE = 100


def _report_range_params(starting_date: str, ending_date: str) -> Dict[str, str]:
    """Params for the usage_report / cost_report endpoints, which take
    RFC 3339 timestamps with an exclusive ``ending_at`` (unlike summaries,
    which takes plain ``starting_date`` / ``ending_date``)."""
    ending_next = date.fromisoformat(ending_date) + timedelta(days=1)
    return {
        "starting_at": "%sT00:00:00Z" % starting_date,
        "ending_at": "%sT00:00:00Z" % ending_next.isoformat(),
        "bucket_width": "1d",
    }


class AnthropicAPI:
    def __init__(self, admin_key, analytics_key=None, proxy_url=None):
        self._client = JsonHttpClient(proxy_url=proxy_url)
        self._admin_key = admin_key
        self._analytics_key = analytics_key or admin_key

    def _admin_headers(self):
        return {
            "x-api-key": self._admin_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }

    def _analytics_headers(self):
        return {
            "Authorization": "Bearer %s" % self._analytics_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }

    def _get(self, path, params=None, headers=None):
        return self._client.get_json(
            ANTHROPIC_API_BASE + path,
            headers=headers or self._admin_headers(),
            params=params,
        )

    def paginate(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data_key: str = "data",
        max_items: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Cursor pagination using after_id / has_more / last_id."""
        query = dict(params or {})
        query.setdefault("limit", min(MAX_PAGE_SIZE, max_items or MAX_PAGE_SIZE))
        collected = 0
        while True:
            response = self._get(path, params=query, headers=headers)
            items = response.get(data_key, [])
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
            query["after_id"] = last_id

    # -- Compliance -------------------------------------------------------
    def list_activities(self, after_id=None, created_at_gte=None, max_items=None):
        params = {"order": "asc"}
        if after_id:
            params["after_id"] = after_id
        if created_at_gte:
            params["created_at.gte"] = created_at_gte
        return self.paginate(
            "/v1/compliance/activities", params=params, max_items=max_items
        )

    def list_users(self, max_items=None):
        return self.paginate("/v1/organizations/users", max_items=max_items)

    def list_groups(self, max_items=None):
        return self.paginate("/v1/organizations/groups", max_items=max_items)

    # -- Analytics --------------------------------------------------------
    def _analytics_paginate(self, path, params):
        query = dict(params or {})
        while True:
            response = self._client.get_json(
                ANTHROPIC_API_BASE + path,
                headers=self._analytics_headers(),
                params=query,
            )
            items = response.get("data", [])
            if isinstance(items, list):
                for item in items:
                    yield item
            next_page = response.get("next_page")
            if not next_page:
                return
            query["page"] = next_page

    def analytics_summaries(self, starting_date, ending_date):
        return self._analytics_paginate(
            "/v1/organizations/analytics/summaries",
            {"starting_date": starting_date, "ending_date": ending_date},
        )

    def analytics_usage(self, starting_date, ending_date):
        return self._analytics_paginate(
            "/v1/organizations/analytics/usage_report",
            _report_range_params(starting_date, ending_date),
        )

    def analytics_cost(self, starting_date, ending_date):
        return self._analytics_paginate(
            "/v1/organizations/analytics/cost_report",
            _report_range_params(starting_date, ending_date),
        )
