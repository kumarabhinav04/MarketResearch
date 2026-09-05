from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class SourceCatalogError(ValueError):
    pass


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    name: str
    category: str
    connector: str
    implementation_status: str
    enabled: bool
    source_tier: str
    publisher: str
    base_url: str
    rate_limit_per_second: float
    timeout_seconds: float
    max_response_bytes: int
    licence_notes: str
    auth: dict[str, Any] = field(default_factory=dict)
    endpoints: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceDefinition":
        required = {
            "id",
            "name",
            "category",
            "connector",
            "implementation_status",
            "enabled",
            "source_tier",
            "publisher",
            "base_url",
            "rate_limit_per_second",
            "timeout_seconds",
            "max_response_bytes",
            "licence_notes",
        }
        missing = required.difference(value)
        if missing:
            raise SourceCatalogError(
                f"Source definition is missing fields: {sorted(missing)}"
            )
        source = cls(**{key: value[key] for key in required},
                     auth=dict(value.get("auth", {})),
                     endpoints=dict(value.get("endpoints", {})),
                     options=dict(value.get("options", {})))
        source.validate()
        return source

    def validate(self) -> None:
        if not self.id.replace("_", "").isalnum():
            raise SourceCatalogError(f"Invalid source id: {self.id}")
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise SourceCatalogError(f"Source {self.id} must use an HTTPS base URL")
        if self.source_tier not in {"1", "2", "3"}:
            raise SourceCatalogError(f"Source {self.id} has an invalid evidence tier")
        if self.rate_limit_per_second <= 0:
            raise SourceCatalogError(f"Source {self.id} rate limit must be positive")
        if self.timeout_seconds <= 0 or self.max_response_bytes <= 0:
            raise SourceCatalogError(f"Source {self.id} limits must be positive")
        auth_type = self.auth.get("type", "none")
        if auth_type not in {"none", "header", "query", "basic_username"}:
            raise SourceCatalogError(f"Source {self.id} has unsupported auth type")
        if auth_type != "none" and not self.auth.get("env"):
            raise SourceCatalogError(f"Source {self.id} auth must reference an env variable")

    @property
    def credential_configured(self) -> bool:
        if self.auth.get("type", "none") == "none":
            return True
        return bool(os.getenv(str(self.auth.get("env", ""))))

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "connector": self.connector,
            "implementation_status": self.implementation_status,
            "enabled": self.enabled,
            "source_tier": self.source_tier,
            "credential_env": self.auth.get("env"),
            "credential_optional": bool(self.auth.get("optional")),
            "credential_configured": self.credential_configured,
            "base_url": self.base_url,
            "rate_limit_per_second": self.rate_limit_per_second,
            "licence_notes": self.licence_notes,
        }


class SourceCatalog:
    def __init__(self, version: str, sources: list[SourceDefinition]):
        self.version = version
        self._sources = {source.id: source for source in sources}
        if len(self._sources) != len(sources):
            raise SourceCatalogError("Source ids must be unique")

    @classmethod
    def load(cls, path: Path) -> "SourceCatalog":
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not payload.get("version") or not isinstance(payload.get("sources"), list):
            raise SourceCatalogError("Source catalog requires version and sources")
        return cls(
            str(payload["version"]),
            [SourceDefinition.from_dict(item) for item in payload["sources"]],
        )

    def get(self, source_id: str) -> SourceDefinition:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise SourceCatalogError(f"Unknown source: {source_id}") from exc

    def list(self) -> list[SourceDefinition]:
        return sorted(self._sources.values(), key=lambda item: (item.category, item.id))
