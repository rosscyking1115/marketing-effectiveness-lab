"""Local artifact registry primitives for generated measurement outputs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

REGISTRY_SCHEMA_VERSION = "1.0"
_INDEX_FILE = "artifact_index.json"
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class ArtifactRecord:
    """Metadata for one persisted artifact payload."""

    registry_schema_version: str
    artifact_type: str
    artifact_id: str
    content_path: str
    content_type: str
    content_sha256: str
    content_bytes: int
    created_at_utc: str
    metadata: dict[str, Any]


def persist_artifact(
    registry_dir: str | Path,
    *,
    artifact_type: str,
    content: str | bytes,
    content_type: str,
    file_extension: str,
    artifact_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at_utc: str | None = None,
) -> ArtifactRecord:
    """Persist an artifact payload and upsert its metadata into the local index."""

    _validate_token(artifact_type, "artifact_type")
    extension = _normalize_extension(file_extension)
    content_bytes = _content_bytes(content)
    content_sha = hashlib.sha256(content_bytes).hexdigest()
    stable_artifact_id = artifact_id or f"{artifact_type}_{content_sha[:16]}"
    _validate_token(stable_artifact_id, "artifact_id")

    root = Path(registry_dir).expanduser().resolve()
    artifact_dir = root / artifact_type
    artifact_dir.mkdir(parents=True, exist_ok=True)

    content_path = artifact_dir / f"{stable_artifact_id}.{extension}"
    _write_bytes(content_path, content_bytes)

    record = ArtifactRecord(
        registry_schema_version=REGISTRY_SCHEMA_VERSION,
        artifact_type=artifact_type,
        artifact_id=stable_artifact_id,
        content_path=content_path.relative_to(root).as_posix(),
        content_type=content_type,
        content_sha256=content_sha,
        content_bytes=len(content_bytes),
        created_at_utc=created_at_utc or _utc_now(),
        metadata=_json_safe_metadata(metadata or {}),
    )
    _upsert_record(root / _INDEX_FILE, record)
    return record


def persist_json_artifact(
    registry_dir: str | Path,
    *,
    artifact_type: str,
    payload: dict[str, Any],
    artifact_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    created_at_utc: str | None = None,
) -> ArtifactRecord:
    """Persist a JSON artifact using stable pretty serialization."""

    payload_text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    return persist_artifact(
        registry_dir,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        content=payload_text,
        content_type="application/json",
        file_extension="json",
        metadata=metadata,
        created_at_utc=created_at_utc,
    )


def load_artifact_index(registry_dir: str | Path) -> list[ArtifactRecord]:
    """Load persisted artifact metadata records from the registry index."""

    index_path = Path(registry_dir).expanduser().resolve() / _INDEX_FILE
    if not index_path.exists():
        return []

    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"Artifact registry index is invalid JSON: {exc.msg}."
        raise ValueError(msg) from exc

    if not isinstance(payload, dict) or payload.get("registry_schema_version") != REGISTRY_SCHEMA_VERSION:
        msg = "Artifact registry index has an unsupported schema version."
        raise ValueError(msg)

    records = payload.get("records")
    if not isinstance(records, list):
        msg = "Artifact registry index must contain a records list."
        raise ValueError(msg)

    return [_record_from_payload(record) for record in records]


def artifact_index_dataframe(
    registry_dir: str | Path,
    *,
    artifact_type: str | None = None,
) -> pd.DataFrame:
    """Return registry metadata as a tabular index for dashboards or review."""

    records = load_artifact_index(registry_dir)
    rows = [asdict(record) for record in records]
    if artifact_type is not None:
        rows = [row for row in rows if row["artifact_type"] == artifact_type]
    return pd.DataFrame(rows, columns=_artifact_index_columns())


def read_artifact_text(registry_dir: str | Path, record: ArtifactRecord) -> str:
    """Read a persisted artifact payload as UTF-8 text."""

    return _artifact_path(registry_dir, record).read_text(encoding="utf-8")


def read_artifact_bytes(registry_dir: str | Path, record: ArtifactRecord) -> bytes:
    """Read a persisted artifact payload as bytes."""

    return _artifact_path(registry_dir, record).read_bytes()


def verify_artifact_content(registry_dir: str | Path, record: ArtifactRecord) -> bool:
    """Check whether the stored payload still matches the indexed SHA-256 hash."""

    payload = read_artifact_bytes(registry_dir, record)
    return hashlib.sha256(payload).hexdigest() == record.content_sha256


def _upsert_record(index_path: Path, record: ArtifactRecord) -> None:
    records = load_artifact_index(index_path.parent)
    filtered = [
        existing
        for existing in records
        if not (
            existing.artifact_type == record.artifact_type
            and existing.artifact_id == record.artifact_id
        )
    ]
    filtered.append(record)
    filtered.sort(key=lambda item: (item.artifact_type, item.artifact_id))
    payload = {
        "registry_schema_version": REGISTRY_SCHEMA_VERSION,
        "records": [asdict(item) for item in filtered],
    }
    _write_text(index_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _record_from_payload(payload: object) -> ArtifactRecord:
    if not isinstance(payload, dict):
        msg = "Artifact registry records must be objects."
        raise ValueError(msg)

    required_fields = set(_artifact_index_columns())
    missing = sorted(required_fields.difference(payload))
    if missing:
        msg = f"Artifact registry record is missing field(s): {', '.join(missing)}."
        raise ValueError(msg)

    metadata = payload["metadata"]
    if not isinstance(metadata, dict):
        msg = "Artifact registry record metadata must be an object."
        raise ValueError(msg)

    return ArtifactRecord(
        registry_schema_version=str(payload["registry_schema_version"]),
        artifact_type=str(payload["artifact_type"]),
        artifact_id=str(payload["artifact_id"]),
        content_path=str(payload["content_path"]),
        content_type=str(payload["content_type"]),
        content_sha256=str(payload["content_sha256"]),
        content_bytes=int(payload["content_bytes"]),
        created_at_utc=str(payload["created_at_utc"]),
        metadata=metadata,
    )


def _artifact_path(registry_dir: str | Path, record: ArtifactRecord) -> Path:
    root = Path(registry_dir).expanduser().resolve()
    artifact_path = (root / record.content_path).resolve()
    if root not in artifact_path.parents and artifact_path != root:
        msg = "Artifact content path escapes the registry directory."
        raise ValueError(msg)
    return artifact_path


def _content_bytes(content: str | bytes) -> bytes:
    if isinstance(content, bytes):
        return content
    return content.encode("utf-8")


def _json_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(metadata, sort_keys=True, default=str))


def _normalize_extension(file_extension: str) -> str:
    extension = file_extension.removeprefix(".")
    _validate_token(extension, "file_extension")
    return extension


def _validate_token(value: str, field_name: str) -> None:
    if not _SAFE_TOKEN_RE.match(value):
        msg = f"{field_name} must contain only letters, numbers, underscores, or hyphens."
        raise ValueError(msg)


def _write_bytes(path: Path, payload: bytes) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_bytes(payload)
    temp_path.replace(path)


def _write_text(path: Path, payload: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _artifact_index_columns() -> list[str]:
    return [
        "registry_schema_version",
        "artifact_type",
        "artifact_id",
        "content_path",
        "content_type",
        "content_sha256",
        "content_bytes",
        "created_at_utc",
        "metadata",
    ]
