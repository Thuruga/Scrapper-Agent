"""Immutable sortiment snapshot and manifest helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.models import SortimentCategorySnapshot, SortimentSnapshotManifest


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SORTIMENT_SNAPSHOT_DIR = DATA_DIR / "sortiment_snapshots"
SORTIMENT_MANIFEST_DIR = DATA_DIR / "sortiment_manifests"


def _safe_artifact_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _timestamp_slug(captured_at: str) -> str:
    normalized = captured_at.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _manifest_path(category_id: str) -> Path:
    return SORTIMENT_MANIFEST_DIR / f"{_safe_artifact_id(category_id)}.json"


def build_sortiment_snapshot_filename(snapshot: SortimentCategorySnapshot) -> str:
    return (
        f"{_safe_artifact_id(snapshot.category_id)}"
        f"__{_timestamp_slug(snapshot.captured_at)}.json"
    )


def load_sortiment_manifest(category_id: str) -> SortimentSnapshotManifest | None:
    data = _read_json(_manifest_path(category_id))
    if data is None:
        return None
    return SortimentSnapshotManifest.model_validate(data)


def load_sortiment_snapshot(filename: str) -> SortimentCategorySnapshot | None:
    data = _read_json(SORTIMENT_SNAPSHOT_DIR / filename)
    if data is None:
        return None
    return SortimentCategorySnapshot.model_validate(data)


def persist_sortiment_snapshot(
    snapshot: SortimentCategorySnapshot | dict[str, Any],
) -> tuple[Path, SortimentSnapshotManifest]:
    validated = SortimentCategorySnapshot.model_validate(snapshot)
    filename = build_sortiment_snapshot_filename(validated)
    snapshot_path = SORTIMENT_SNAPSHOT_DIR / filename
    _write_json(snapshot_path, validated.model_dump(mode="json"))

    previous_manifest = load_sortiment_manifest(validated.category_id)
    previous_snapshot = previous_manifest.latest_snapshot if previous_manifest else None
    previous_snapshot_at = (
        previous_manifest.latest_snapshot_at if previous_manifest else None
    )
    if previous_snapshot == filename:
        previous_snapshot = previous_manifest.previous_snapshot
        previous_snapshot_at = previous_manifest.previous_snapshot_at

    manifest = SortimentSnapshotManifest(
        category_id=validated.category_id,
        latest_snapshot=filename,
        previous_snapshot=previous_snapshot,
        latest_snapshot_at=validated.captured_at,
        previous_snapshot_at=previous_snapshot_at,
    )
    _write_json(_manifest_path(validated.category_id), manifest.model_dump(mode="json"))
    return snapshot_path, manifest
