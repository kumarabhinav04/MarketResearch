from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse


PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"system\s+prompt",
        r"developer\s+message",
        r"reveal\s+(your|the)\s+(prompt|instructions|secret)",
        r"call\s+(this\s+)?tool",
        r"exfiltrat(e|ion)",
    )
]


class UnsafeSourceError(ValueError):
    pass


def detect_prompt_injection(text: str) -> list[str]:
    matches: list[str] = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(text):
            matches.append(pattern.pattern)
    return matches


def validate_external_url(url: str, resolve_dns: bool = False) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise UnsafeSourceError("Only HTTPS source URLs are permitted")
    if not parsed.hostname:
        raise UnsafeSourceError("Source URL must include a hostname")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeSourceError("Local hosts are not permitted")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if resolve_dns:
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
                _reject_ip(ipaddress.ip_address(item[4][0]))
    else:
        _reject_ip(ip)


def _reject_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise UnsafeSourceError(f"Source address {ip} is not publicly routable")


def redact_secret(value: str, secret: str) -> str:
    if secret:
        return value.replace(secret, "[REDACTED]")
    return value
