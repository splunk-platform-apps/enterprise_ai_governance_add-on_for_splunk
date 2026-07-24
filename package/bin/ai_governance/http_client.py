"""Minimal HTTPS JSON client with retry/backoff and optional proxy.

Uses only the Python standard library so the add-on stays lightweight and
Splunk Cloud friendly. TLS certificate verification is always enabled
(default urllib behaviour).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from ai_governance import ADDON_NAME, ADDON_VERSION

logger = logging.getLogger("ta_ai_governance_http")

DEFAULT_TIMEOUT = 60
MAX_RETRIES = 5


class APIError(Exception):
    """Raised when a provider API returns an error response."""

    def __init__(self, status_code, message, response_body=None):
        super(APIError, self).__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class JsonHttpClient:
    """HTTPS client for provider REST APIs."""

    def __init__(self, proxy_url=None, timeout=DEFAULT_TIMEOUT, allow_http=False):
        self.timeout = timeout
        self.allow_http = allow_http
        self._proxy_handler = None
        if proxy_url:
            self._proxy_handler = urllib.request.ProxyHandler(
                {"http": proxy_url, "https": proxy_url}
            )

    def _opener(self):
        if self._proxy_handler:
            return urllib.request.build_opener(self._proxy_handler)
        return urllib.request.build_opener()

    def request_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        form_body: Optional[Dict[str, str]] = None,
        raw_text: bool = False,
    ) -> Any:
        """Perform an HTTPS request and return the parsed JSON body
        (or the raw text body when ``raw_text`` is set).

        Retries on 429 (honouring Retry-After), 5xx and transient network
        errors with exponential backoff.
        """
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                sep = "&" if "?" in url else "?"
                url = url + sep + urllib.parse.urlencode(filtered, doseq=True)

        lowered = url.lower()
        if not lowered.startswith("https://"):
            # Plain HTTP is only permitted when the account explicitly
            # opts in (self-hosted lab servers on trusted networks).
            if not (self.allow_http and lowered.startswith("http://")):
                raise APIError(0, "Only HTTPS endpoints are supported")

        all_headers = {
            "Accept": "application/json",
            "User-Agent": "%s/%s" % (ADDON_NAME, ADDON_VERSION),
        }
        if headers:
            all_headers.update(headers)

        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            all_headers["Content-Type"] = "application/json"
        elif form_body is not None:
            data = urllib.parse.urlencode(form_body).encode("utf-8")
            all_headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(
            url, data=data, method=method, headers=all_headers
        )
        opener = self._opener()
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                with opener.open(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    if raw_text:
                        return body
                    if not body:
                        return {}
                    return json.loads(body)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                retryable = exc.code == 429 or exc.code >= 500
                if retryable and attempt < MAX_RETRIES - 1:
                    retry_after = exc.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        sleep_seconds = min(int(retry_after), 120)
                    else:
                        sleep_seconds = 2**attempt
                    logger.warning(
                        "HTTP %s from %s, retrying in %ss (attempt %s/%s)",
                        exc.code,
                        urllib.parse.urlsplit(url).netloc,
                        sleep_seconds,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(sleep_seconds)
                    last_error = exc
                    continue
                message = _parse_error_message(body) or str(exc.reason)
                raise APIError(exc.code, message, body)
            except urllib.error.URLError as exc:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                    last_error = exc
                    continue
                raise APIError(0, "Network error: %s" % exc.reason)

        raise APIError(0, "Request failed after retries: %s" % last_error)

    def get_json(self, url, headers=None, params=None):
        return self.request_json("GET", url, headers=headers, params=params)

    def get_text(self, url, headers=None, params=None):
        return self.request_json(
            "GET", url, headers=headers, params=params, raw_text=True
        )

    def post_json(self, url, headers=None, json_body=None):
        return self.request_json("POST", url, headers=headers, json_body=json_body)

    def post_form(self, url, form_body, headers=None):
        return self.request_json("POST", url, headers=headers, form_body=form_body)


def _parse_error_message(body):
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return None
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("type") or error.get("code")
        if isinstance(error, str):
            return error
        return payload.get("error_description") or payload.get("message")
    return None
