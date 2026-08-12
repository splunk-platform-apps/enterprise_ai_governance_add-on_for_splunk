"""OpenAI ChatGPT Enterprise Compliance Logs Platform client.

This is a different surface from :mod:`ai_governance.providers.openai_api`:

============  ======================================  =========================
Surface       Host                                    Credential
============  ======================================  =========================
Platform      ``api.openai.com/v1/organization``      Admin key (``sk-admin-``)
Compliance    ``api.chatgpt.com/v1/compliance``       Compliance API key
============  ======================================  =========================

The platform exposes immutable, time-windowed JSONL log files. Collection is
a two-step flow per the OpenAI quickstart: list the available files for an
``event_type`` after a watermark, then download each file by id. Listing
returns ``data`` (file descriptors), ``has_more`` and ``last_end_time``; the
``last_end_time`` of a page is the ``after`` value for the next page and the
resumable watermark for the next collection cycle.

Reference: https://cookbook.openai.com/examples/chatgpt/compliance_api/logs_platform
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import quote

from ai_governance import OPENAI_COMPLIANCE_API_BASE
from ai_governance.http_client import JsonHttpClient

MAX_PAGE_SIZE = 100

# Log file bodies are JSONL, not JSON. Ask for it, but stay permissive because
# the download 302s to object storage, which serves its own content type.
_DOWNLOAD_ACCEPT = "application/x-ndjson, application/jsonl;q=0.9, */*;q=0.8"


class OpenAIComplianceAPI:
    """Client for the Compliance Logs Platform list/download endpoints."""

    def __init__(self, compliance_key: str, principal_id: str, proxy_url=None):
        self._client = JsonHttpClient(proxy_url=proxy_url)
        self._key = compliance_key
        self._principal_id = (principal_id or "").strip()
        if not self._principal_id:
            raise ValueError(
                "A ChatGPT workspace ID or API Platform organization ID is "
                "required to call the Compliance API"
            )
        # An API Platform org id is addressed under /organizations; a ChatGPT
        # workspace id (a UUID) is addressed under /workspaces.
        self._scope_segment = (
            "organizations" if self._principal_id.startswith("org-") else "workspaces"
        )

    @property
    def scope_segment(self) -> str:
        return self._scope_segment

    @property
    def principal_id(self) -> str:
        return self._principal_id

    def _headers(self, accept: str = "application/json") -> Dict[str, str]:
        return {
            "Authorization": "Bearer %s" % self._key,
            "Accept": accept,
        }

    def _logs_url(self, suffix: str = "") -> str:
        return "%s/%s/%s/logs%s" % (
            OPENAI_COMPLIANCE_API_BASE,
            self._scope_segment,
            quote(self._principal_id, safe=""),
            suffix,
        )

    def iter_log_pages(
        self,
        event_type: str,
        after: str,
        limit: int = MAX_PAGE_SIZE,
    ) -> Iterator[Tuple[List[Dict[str, Any]], Optional[str], bool]]:
        """Yield ``(file_descriptors, last_end_time, has_more)`` per page.

        The caller is expected to fully process a page (download and emit
        every file) before advancing its checkpoint to that page's
        ``last_end_time``, so an interrupted cycle resumes without gaps.
        """
        current_after = after
        while True:
            response = self._client.get_json(
                self._logs_url(),
                headers=self._headers(),
                params={
                    "limit": min(limit, MAX_PAGE_SIZE),
                    "event_type": event_type,
                    "after": current_after,
                },
            )
            files = response.get("data")
            files = files if isinstance(files, list) else []
            last_end_time = response.get("last_end_time")
            has_more = bool(response.get("has_more"))

            yield files, last_end_time, has_more

            # Stop unless the server both promises more and moves the
            # watermark forward - a repeated last_end_time would loop forever.
            if not has_more or not last_end_time or last_end_time == current_after:
                return
            current_after = last_end_time

    def download_log(self, file_id: str) -> str:
        """Download one log file and return its raw JSONL body."""
        return self._client.get_text(
            self._logs_url("/%s" % quote(str(file_id), safe="")),
            headers=self._headers(accept=_DOWNLOAD_ACCEPT),
        )


def parse_jsonl(body: str) -> Iterator[Dict[str, Any]]:
    """Yield the JSON objects in a JSONL body, skipping unparseable lines.

    A single malformed line must not cost the rest of the file: these are
    compliance records, and dropping a whole window loses evidence.
    """
    for line in (body or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            yield record
        elif isinstance(record, list):
            for item in record:
                if isinstance(item, dict):
                    yield item
