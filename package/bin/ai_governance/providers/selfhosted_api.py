"""Client for self-hosted / open-source LLM servers.

Supports any OpenAI-compatible endpoint (vLLM, LiteLLM proxy, llama.cpp
server, text-generation-inference with the OpenAI shim, etc.) plus native
Ollama endpoints. Collects governance-relevant signals only:

- model inventory (``/v1/models`` or Ollama ``/api/tags``)
- runtime state (Ollama ``/api/ps``: models currently loaded)
- Prometheus metrics (vLLM / LiteLLM ``/metrics``)
"""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ai_governance.http_client import JsonHttpClient

SERVER_OPENAI_COMPATIBLE = "openai_compatible"
SERVER_VLLM = "vllm"
SERVER_OLLAMA = "ollama"
SERVER_LITELLM = "litellm"

PROMETHEUS_SERVERS = (SERVER_OPENAI_COMPATIBLE, SERVER_VLLM, SERVER_LITELLM)


class SelfHostedAPI:
    def __init__(
        self,
        base_url: str,
        server_type: str = SERVER_OPENAI_COMPATIBLE,
        api_key: Optional[str] = None,
        allow_http: bool = False,
        proxy_url: Optional[str] = None,
    ):
        self._base = base_url.rstrip("/")
        self._server_type = server_type or SERVER_OPENAI_COMPATIBLE
        self._api_key = api_key
        self._client = JsonHttpClient(proxy_url=proxy_url, allow_http=allow_http)

    @property
    def server_type(self) -> str:
        return self._server_type

    def _headers(self) -> Dict[str, str]:
        if self._api_key:
            return {"Authorization": "Bearer %s" % self._api_key}
        return {}

    def _get(self, path: str) -> Any:
        return self._client.get_json(self._base + path, headers=self._headers())

    # -- Model inventory ---------------------------------------------------
    def list_models(self) -> Tuple[List[Dict[str, Any]], float]:
        """Return (models, latency_seconds). Model dicts are normalized to
        always carry a ``model_id`` key."""
        started = time.time()
        if self._server_type == SERVER_OLLAMA:
            response = self._get("/api/tags")
            raw = response.get("models", []) or []
            models = []
            for item in raw:
                model = dict(item)
                model["model_id"] = item.get("name") or item.get("model")
                models.append(model)
        else:
            response = self._get("/v1/models")
            raw = response.get("data", []) or []
            models = []
            for item in raw:
                model = dict(item)
                model["model_id"] = item.get("id")
                models.append(model)
        latency = time.time() - started
        return [m for m in models if m.get("model_id")], latency

    # -- Runtime state (Ollama) ---------------------------------------------
    def running_models(self) -> List[Dict[str, Any]]:
        if self._server_type != SERVER_OLLAMA:
            return []
        response = self._get("/api/ps")
        models = response.get("models", []) or []
        out = []
        for item in models:
            model = dict(item)
            model["model_id"] = item.get("name") or item.get("model")
            out.append(model)
        return out

    # -- Prometheus metrics --------------------------------------------------
    def scrape_metrics(
        self, metrics_path: str = "/metrics", prefixes: Optional[List[str]] = None
    ) -> Iterator[Dict[str, Any]]:
        """Parse Prometheus text exposition format into metric sample dicts.

        Yields ``{"metric_name": ..., "value": ..., <label>: <value>, ...}``
        for every sample whose family name starts with one of ``prefixes``
        (all samples if no prefixes are given).
        """
        path = "/" + metrics_path.lstrip("/")
        text = self._client.get_text(self._base + path, headers=self._headers())
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sample = _parse_prometheus_line(line)
            if not sample:
                continue
            if prefixes and not any(
                sample["metric_name"].startswith(p) for p in prefixes
            ):
                continue
            yield sample


def _parse_prometheus_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse one exposition line: ``name{l1="v1",l2="v2"} value [ts]``."""
    try:
        if "{" in line:
            name, rest = line.split("{", 1)
            labels_part, value_part = rest.rsplit("}", 1)
        else:
            parts = line.split()
            if len(parts) < 2:
                return None
            name, labels_part, value_part = parts[0], "", " ".join(parts[1:])
        value_tokens = value_part.strip().split()
        if not value_tokens:
            return None
        value = float(value_tokens[0])
        sample: Dict[str, Any] = {"metric_name": name.strip(), "value": value}
        if labels_part:
            for pair in _split_labels(labels_part):
                if "=" not in pair:
                    continue
                key, _, raw = pair.partition("=")
                sample[key.strip()] = raw.strip().strip('"')
        return sample
    except (ValueError, IndexError):
        return None


def _split_labels(labels_part: str) -> List[str]:
    """Split label pairs on commas outside quoted values."""
    pairs = []
    current = []
    in_quotes = False
    escaped = False
    for char in labels_part:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\":
            current.append(char)
            escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
            continue
        if char == "," and not in_quotes:
            pairs.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        pairs.append("".join(current))
    return pairs
