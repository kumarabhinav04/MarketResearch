from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RawSnapshot:
    content_hash: str
    content_path: Path
    manifest_path: Path
    byte_count: int


class RawSnapshotStore:
    """Content-addressed local raw zone; replace with S3/MinIO behind this interface."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(
        self,
        source_id: str,
        body: bytes,
        *,
        source_url: str,
        content_type: str,
        external_id: str,
        headers: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RawSnapshot:
        digest = hashlib.sha256(body).hexdigest()
        now = datetime.now(UTC)
        directory = self.root / source_id / now.strftime("%Y/%m/%d") / digest[:2]
        directory.mkdir(parents=True, exist_ok=True)
        extension = _extension(content_type)
        content_path = directory / f"{digest}.{extension}"
        manifest_path = directory / f"{digest}.manifest.json"
        if not content_path.exists():
            temporary = content_path.with_suffix(f".{extension}.tmp")
            temporary.write_bytes(body)
            temporary.replace(content_path)
        manifest = {
            "schema_version": "1.0",
            "source_id": source_id,
            "external_id": external_id,
            "source_url": source_url,
            "content_type": content_type,
            "content_hash": digest,
            "byte_count": len(body),
            "retrieved_at": now.isoformat(),
            "response_headers": headers or {},
            "metadata": metadata or {},
        }
        if not manifest_path.exists():
            temporary_manifest = manifest_path.with_suffix(".json.tmp")
            temporary_manifest.write_text(
                json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
            )
            temporary_manifest.replace(manifest_path)
        return RawSnapshot(digest, content_path, manifest_path, len(body))

    def put_normalized_text(self, snapshot: RawSnapshot, text: str) -> Path:
        path = snapshot.content_path.with_suffix(".normalized.txt")
        if not path.exists():
            temporary = path.with_suffix(".txt.tmp")
            temporary.write_text(text, encoding="utf-8")
            temporary.replace(path)
        return path


def _extension(content_type: str) -> str:
    normalized = content_type.split(";", 1)[0].strip().lower()
    return {
        "application/json": "json",
        "text/json": "json",
        "text/html": "html",
        "application/xhtml+xml": "xhtml",
        "application/pdf": "pdf",
        "text/plain": "txt",
        "application/zip": "zip",
    }.get(normalized, "bin")
