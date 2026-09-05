from __future__ import annotations

import contextvars
import json
import logging
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Iterator


run_id_context: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="")
company_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "company_id", default=""
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": run_id_context.get(),
            "company_id": company_id_context.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for name in ("event", "agent", "duration_ms", "status"):
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


@dataclass
class MetricsRegistry:
    counters: Counter = field(default_factory=Counter)
    durations: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    _lock: Lock = field(default_factory=Lock)

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self.counters[name] += amount

    def observe(self, name: str, seconds: float) -> None:
        with self._lock:
            self.durations[name].append(seconds)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, value in sorted(self.counters.items()):
                metric = _metric_name(name)
                lines.extend([f"# TYPE {metric} counter", f"{metric} {value}"])
            for name, observations in sorted(self.durations.items()):
                metric = _metric_name(name)
                count = len(observations)
                total = sum(observations)
                lines.extend(
                    [
                        f"# TYPE {metric}_seconds summary",
                        f"{metric}_seconds_count {count}",
                        f"{metric}_seconds_sum {total:.6f}",
                    ]
                )
        return "\n".join(lines) + "\n"


def _metric_name(value: str) -> str:
    return "aifactory_" + "".join(char if char.isalnum() else "_" for char in value)


METRICS = MetricsRegistry()


@contextmanager
def timed_operation(name: str, logger: logging.Logger, **extra: str) -> Iterator[None]:
    started = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        METRICS.increment(f"{name}_errors_total")
        raise
    finally:
        duration = time.perf_counter() - started
        METRICS.observe(name, duration)
        log_method = logger.debug if name == "agent_execution" else logger.info
        log_method(
            "%s completed",
            name,
            extra={"event": name, "duration_ms": round(duration * 1000, 2), "status": status, **extra},
        )
