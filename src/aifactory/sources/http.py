from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import certifi
import httpx

from ..security import validate_external_url
from ..telemetry import METRICS, timed_operation
from .catalog import SourceDefinition


logging.getLogger("httpx").setLevel(logging.WARNING)


class SourceRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResponse:
    url: str
    status_code: int
    body: bytes
    headers: dict[str, str]

    @property
    def not_modified(self) -> bool:
        return self.status_code == 304

    def json(self) -> Any:
        try:
            return __import__("json").loads(self.body)
        except (ValueError, UnicodeDecodeError) as exc:
            raise SourceRequestError("Source returned invalid JSON") from exc


class SourceHttpClient:
    """Bounded HTTPS client with per-source rate limits and sanitized errors."""

    def __init__(
        self,
        definition: SourceDefinition,
        user_agent: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.definition = definition
        self.user_agent = user_agent
        self._last_request_at = 0.0
        self._client = httpx.Client(
            verify=certifi.where(),
            timeout=httpx.Timeout(definition.timeout_seconds),
            follow_redirects=False,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SourceHttpClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        conditional: dict[str, Any] | None = None,
        attempts: int | None = None,
    ) -> FetchResponse:
        url = endpoint if endpoint.startswith("https://") else urljoin(
            f"{self.definition.base_url.rstrip('/')}/", endpoint.lstrip("/")
        )
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/html,application/xhtml+xml,application/pdf",
            "Accept-Encoding": "gzip, deflate",
        }
        if conditional:
            if conditional.get("etag"):
                headers["If-None-Match"] = str(conditional["etag"])
            if conditional.get("last_modified"):
                headers["If-Modified-Since"] = str(conditional["last_modified"])
        request_params = dict(params or {})
        auth: httpx.Auth | None = None
        self._apply_auth(headers, request_params)
        if self.definition.auth.get("type") == "basic_username":
            auth = httpx.BasicAuth(self._credential(), "")

        attempt_count = attempts or int(self.definition.options.get("max_attempts", 4))
        attempt_count = max(1, min(attempt_count, 8))
        last_error: Exception | None = None
        for attempt in range(attempt_count):
            try:
                response = self._send_with_safe_redirects(
                    method,
                    url,
                    headers=headers,
                    params=request_params,
                    json_body=json_body,
                    auth=auth,
                )
                if response.status_code == 304:
                    return FetchResponse(url, 304, b"", _safe_headers(response.headers))
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = _retry_after(response.headers.get("retry-after"), attempt)
                    response.close()
                    if attempt + 1 < attempt_count:
                        METRICS.increment("source_fetch_retry_total")
                        time.sleep(retry_after)
                        continue
                if response.status_code >= 400:
                    status = response.status_code
                    response.close()
                    raise SourceRequestError(
                        f"{self.definition.id} request failed with HTTP {status}"
                    )
                body = response.content
                safe_headers = _safe_headers(response.headers)
                response.close()
                if len(body) > self.definition.max_response_bytes:
                    raise SourceRequestError(
                        f"{self.definition.id} response exceeded configured size limit"
                    )
                METRICS.increment("source_fetch_total")
                return FetchResponse(url, response.status_code, body, safe_headers)
            except SourceRequestError:
                raise
            except (httpx.HTTPError, TimeoutError) as exc:
                last_error = exc
                METRICS.increment("source_fetch_retry_total")
                if attempt + 1 < attempt_count:
                    time.sleep(min(2**attempt, 8))
        raise SourceRequestError(
            f"{self.definition.id} request failed: {type(last_error).__name__}"
        ) from last_error

    def _send_with_safe_redirects(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any],
        json_body: Any,
        auth: httpx.Auth | None,
    ) -> httpx.Response:
        current_url = url
        current_params: dict[str, Any] | None = params
        for _ in range(6):
            try:
                validate_external_url(current_url, resolve_dns=True)
            except (OSError, ValueError) as exc:
                raise SourceRequestError(
                    f"{self.definition.id} endpoint validation failed: {type(exc).__name__}"
                ) from exc
            self._wait_for_rate_limit()
            with timed_operation("source_fetch", __import__("logging").getLogger(__name__)):
                response = self._client.request(
                    method,
                    current_url,
                    headers=headers,
                    params=current_params,
                    json=json_body,
                    auth=auth,
                )
            self._last_request_at = time.monotonic()
            if not response.is_redirect:
                return response
            location = response.headers.get("location")
            response.close()
            if not location:
                raise SourceRequestError("Source returned an invalid redirect")
            current_url = urljoin(str(response.url), location)
            current_params = None
        raise SourceRequestError("Source exceeded the redirect limit")

    def _wait_for_rate_limit(self) -> None:
        interval = 1.0 / self.definition.rate_limit_per_second
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < interval:
            time.sleep(interval - elapsed)

    def _credential(self) -> str:
        env_name = str(self.definition.auth.get("env", ""))
        value = os.getenv(env_name, "")
        if not value and not self.definition.auth.get("optional"):
            raise SourceRequestError(
                f"{self.definition.id} requires credential environment variable {env_name}"
            )
        return value

    def _apply_auth(
        self, headers: dict[str, str], params: dict[str, Any]
    ) -> None:
        auth_type = self.definition.auth.get("type", "none")
        if auth_type == "none" or auth_type == "basic_username":
            return
        credential = self._credential()
        if not credential:
            return
        name = str(self.definition.auth.get("name", ""))
        if auth_type == "header":
            headers[name] = credential
        elif auth_type == "query":
            params[name] = credential


def _safe_headers(headers: httpx.Headers) -> dict[str, str]:
    allowed = {
        "content-type",
        "content-length",
        "etag",
        "last-modified",
        "date",
        "cache-control",
        "retry-after",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "ratelimit-limit",
        "ratelimit-remaining",
        "ratelimit-reset",
    }
    return {key.lower(): value for key, value in headers.items() if key.lower() in allowed}


def _retry_after(value: str | None, attempt: int) -> float:
    try:
        return min(max(float(value or 0), 0.25), 30.0)
    except ValueError:
        return min(2**attempt, 8)
