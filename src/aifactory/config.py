from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_env_file(path: Path) -> None:
    """Load a simple dotenv file without overwriting process-level configuration."""
    if not path.is_file():
        return
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        name, separator, value = line.partition("=")
        name = name.strip()
        if not separator or not _ENV_NAME.fullmatch(name):
            raise ValueError(f"Invalid dotenv entry at {path}:{line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc


@dataclass(frozen=True)
class Settings:
    environment: str
    db_path: Path
    config_dir: Path
    report_dir: Path
    raw_source_dir: Path
    api_key: str
    log_level: str
    max_workers: int
    min_evidence_confidence: float
    model_provider: str
    model_name: str
    model_base_url: str
    model_api_key: str
    model_timeout_seconds: int
    model_max_completion_tokens: int
    model_reasoning_effort: str
    otel_endpoint: str
    sec_user_agent: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            environment=os.getenv("AIFACTORY_ENV", "development"),
            db_path=Path(os.getenv("AIFACTORY_DB_PATH", "artifacts/aifactory.db")),
            config_dir=Path(os.getenv("AIFACTORY_CONFIG_DIR", "config")),
            report_dir=Path(os.getenv("AIFACTORY_REPORT_DIR", "artifacts/reports")),
            raw_source_dir=Path(
                os.getenv("AIFACTORY_RAW_SOURCE_DIR", "artifacts/raw-sources")
            ),
            api_key=os.getenv("AIFACTORY_API_KEY", "local-development-key"),
            log_level=os.getenv("AIFACTORY_LOG_LEVEL", "INFO").upper(),
            max_workers=max(1, _env_int("AIFACTORY_MAX_WORKERS", 4)),
            min_evidence_confidence=_env_float(
                "AIFACTORY_MIN_EVIDENCE_CONFIDENCE", 0.65
            ),
            model_provider=os.getenv("AIFACTORY_MODEL_PROVIDER", "offline"),
            model_name=os.getenv("AIFACTORY_MODEL_NAME", ""),
            model_base_url=os.getenv(
                "AIFACTORY_MODEL_BASE_URL", "http://localhost:11434"
            ).rstrip("/"),
            model_api_key=os.getenv("AIFACTORY_MODEL_API_KEY", ""),
            model_timeout_seconds=max(
                1, _env_int("AIFACTORY_MODEL_TIMEOUT_SECONDS", 120)
            ),
            model_max_completion_tokens=max(
                16, _env_int("AIFACTORY_MODEL_MAX_COMPLETION_TOKENS", 800)
            ),
            model_reasoning_effort=os.getenv(
                "AIFACTORY_MODEL_REASONING_EFFORT", ""
            ).strip(),
            otel_endpoint=os.getenv("AIFACTORY_OTEL_ENDPOINT", ""),
            sec_user_agent=os.getenv(
                "AIFACTORY_SEC_USER_AGENT", "AI-Factory-Research research@example.com"
            ),
        )

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.raw_source_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, filename: str) -> dict[str, Any]:
        path = self.config_dir / filename
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def get_settings() -> Settings:
    load_env_file(Path(os.getenv("AIFACTORY_ENV_FILE", ".env")))
    settings = Settings.from_env()
    settings.ensure_directories()
    return settings
