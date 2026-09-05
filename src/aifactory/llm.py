from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import certifi

from .config import Settings
from .security import validate_external_url


class ModelGatewayError(RuntimeError):
    pass


class ModelGateway(ABC):
    provider: str

    @abstractmethod
    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_completion_tokens: int | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


class OfflineModelGateway(ModelGateway):
    provider = "offline"

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_completion_tokens: int | None = None,
    ) -> dict[str, Any]:
        raise ModelGatewayError(
            "Offline mode does not call an LLM. Structured evidence agents remain available."
        )


class OpenAICompatibleGateway(ModelGateway):
    provider = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: float = 120,
        max_completion_tokens: int = 800,
        reasoning_effort: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.max_completion_tokens = max_completion_tokens
        self.reasoning_effort = reasoning_effort

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_completion_tokens: int | None = None,
    ) -> dict[str, Any]:
        url = _chat_completions_url(self.base_url)
        _validate_model_endpoint(url)
        constrained_user_prompt = (
            f"{user_prompt}\n\nOUTPUT CONTRACT\n"
            "Return only one JSON object matching this schema. Do not repeat the schema "
            "or add Markdown fences.\n"
            f"{json.dumps(schema, sort_keys=True)}"
        )
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "max_completion_tokens": (
                max_completion_tokens or self.max_completion_tokens
            ),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": constrained_user_prompt},
            ],
        }
        if self.reasoning_effort:
            payload["reasoning"] = {
                "effort": self.reasoning_effort,
                "exclude": True,
            }
        headers = {
            "Content-Type": "application/json",
            "X-Title": "AI Factory Research Platform",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=ssl.create_default_context(cafile=certifi.where()),
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            parsed = _parse_json_object(content)
            _validate_required_keys(parsed, schema)
            return parsed
        except urllib.error.HTTPError as exc:
            raise ModelGatewayError(f"Model request failed with HTTP {exc.code}") from exc
        except ModelGatewayError:
            raise
        except Exception as exc:
            raise ModelGatewayError(f"Model request failed: {type(exc).__name__}") from exc


class OllamaGateway(ModelGateway):
    provider = "ollama"

    def __init__(self, base_url: str, model_name: str, timeout: float = 120):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
        max_completion_tokens: int | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        _validate_model_endpoint(url)
        payload = {
            "model": self.model_name,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                **(
                    {"num_predict": max_completion_tokens}
                    if max_completion_tokens
                    else {}
                ),
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
            parsed = json.loads(result["message"]["content"])
            _validate_required_keys(parsed, schema)
            return parsed
        except Exception as exc:
            raise ModelGatewayError(f"Ollama request failed: {type(exc).__name__}") from exc


class PromptRegistry:
    def __init__(self, prompt_dir: Path):
        self.prompt_dir = prompt_dir

    def render(self, role: str, as_of_date: str, role_file: str | None = None) -> str:
        common = (self.prompt_dir / "common.txt").read_text(encoding="utf-8")
        prompt = common.format(agent_role=role, as_of_date=as_of_date)
        if role_file:
            prompt += "\nROLE-SPECIFIC RUBRIC\n" + (
                self.prompt_dir / role_file
            ).read_text(encoding="utf-8")
        return prompt


def gateway_from_settings(settings: Settings) -> ModelGateway:
    if settings.model_provider == "offline":
        return OfflineModelGateway()
    if settings.model_provider == "openai_compatible":
        if not settings.model_name:
            raise ModelGatewayError("AIFACTORY_MODEL_NAME is required")
        return OpenAICompatibleGateway(
            settings.model_base_url,
            settings.model_api_key,
            settings.model_name,
            timeout=settings.model_timeout_seconds,
            max_completion_tokens=settings.model_max_completion_tokens,
            reasoning_effort=settings.model_reasoning_effort,
        )
    if settings.model_provider == "ollama":
        if not settings.model_name:
            raise ModelGatewayError("AIFACTORY_MODEL_NAME is required")
        return OllamaGateway(settings.model_base_url, settings.model_name)
    raise ModelGatewayError(f"Unsupported model provider: {settings.model_provider}")


def _validate_required_keys(value: dict[str, Any], schema: dict[str, Any]) -> None:
    missing = set(schema.get("required", [])).difference(value)
    if missing:
        raise ModelGatewayError(f"Model output missing keys: {sorted(missing)}")


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _parse_json_object(content: str) -> dict[str, Any]:
    candidate = content.strip()
    if candidate.startswith("```"):
        first_newline = candidate.find("\n")
        last_fence = candidate.rfind("```")
        if first_newline >= 0 and last_fence > first_newline:
            candidate = candidate[first_newline + 1 : last_fence].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        opening_brace = candidate.find("{")
        if opening_brace < 0:
            raise ModelGatewayError("Model output did not contain a JSON object") from None
        try:
            parsed, _ = json.JSONDecoder().raw_decode(candidate[opening_brace:])
        except json.JSONDecodeError as exc:
            raise ModelGatewayError("Model output contained invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ModelGatewayError("Model output must be a JSON object")
    return parsed


def _validate_model_endpoint(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https":
        validate_external_url(url, resolve_dns=False)
        return
    if parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}:
        return
    raise ModelGatewayError("Model endpoints must use HTTPS or a local loopback HTTP address")
