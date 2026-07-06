"""Separate sortiment registry seeded one-way from monitored categories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.models import SortimentCategoryRow


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
MONITORS_FILE = DATA_DIR / "monitored_categories.json"
SORTIMENT_REGISTRY_FILE = DATA_DIR / "sortiment_categories.json"


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_sortiment_categories(enabled_only: bool = False) -> list[SortimentCategoryRow]:
    raw_rows = _read_json(SORTIMENT_REGISTRY_FILE)
    if not isinstance(raw_rows, list):
        return []

    rows = [
        SortimentCategoryRow.model_validate(item)
        for item in raw_rows
        if isinstance(item, dict)
    ]
    if enabled_only:
        return [row for row in rows if row.enabled]
    return rows


def save_sortiment_categories(
    rows: list[SortimentCategoryRow | dict[str, Any]],
) -> list[SortimentCategoryRow]:
    validated = [SortimentCategoryRow.model_validate(row) for row in rows]
    _write_json(
        SORTIMENT_REGISTRY_FILE,
        [row.model_dump(mode="json") for row in validated],
    )
    return validated


def sync_sortiment_categories_from_monitor() -> list[SortimentCategoryRow]:
    monitored_rows = _read_json(MONITORS_FILE)
    if not isinstance(monitored_rows, list):
        return load_sortiment_categories()

    existing_rows = load_sortiment_categories()
    existing_by_source = {
        row.source_monitor_id: row for row in existing_rows if row.source_monitor_id
    }

    synced_rows: list[SortimentCategoryRow] = []
    seen_sources: set[str] = set()

    for item in monitored_rows:
        if not isinstance(item, dict):
            continue
        source_monitor_id = str(item.get("id") or "").strip()
        brand = str(item.get("brand") or "").strip()
        url = str(item.get("url") or "").strip()
        if not source_monitor_id or not brand or not url:
            continue

        current = existing_by_source.get(source_monitor_id)
        now = _now_iso()
        row_payload: dict[str, Any] = {
            "source_monitor_id": source_monitor_id,
            "brand": brand,
            "url": url,
            "enabled": current.enabled if current else False,
            "source_status": item.get("status"),
            "source_last_scraped_at": item.get("last_scraped_at"),
            "last_snapshot_at": current.last_snapshot_at if current else None,
            "last_sync_at": now,
            "updated_at": now,
        }
        if current:
            row_payload["id"] = current.id
        synced_rows.append(
            SortimentCategoryRow(**row_payload)
        )
        seen_sources.add(source_monitor_id)

    orphan_rows = [
        row
        for row in existing_rows
        if row.source_monitor_id and row.source_monitor_id not in seen_sources
    ]
    persisted = save_sortiment_categories(synced_rows + orphan_rows)
    return persisted
