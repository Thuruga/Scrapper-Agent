"""Runtime execution and dashboard assembly for sortiment snapshots."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from config import settings
from core.models import (
    SortimentBucketDelta,
    SortimentBucketEvidence,
    SortimentBucketSnapshot,
    SortimentCategoryRow,
    SortimentCategorySnapshot,
    SortimentDashboardDimension,
    SortimentDashboardResponse,
    SortimentDimension,
    SortimentDimensionSnapshot,
)
from services.engines.factory import engine_factory
from services.sortiment_artifact_service import (
    load_sortiment_manifest,
    load_sortiment_snapshot,
    persist_sortiment_snapshot,
)
from services.sortiment_registry_service import (
    get_sortiment_category,
    load_sortiment_categories,
    update_sortiment_category,
)
from services.stock_summary_service import ensure_scan_product_ids


NOT_INFORMED_LABEL = "não informado"
SORTIMENT_DIMENSIONS: tuple[SortimentDimension, ...] = (
    "available_colors",
    "available_sizes",
    "composition",
)
DIRTY_BUCKET_VALUES = {
    "",
    "-",
    "—",
    "n/a",
    "na",
    "null",
    "none",
    "sem informacao",
    "sem informação",
    "nao informado",
    "não informado",
}
SORTIMENT_RUN_GUARD = asyncio.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _snapshot_id(category_id: str, captured_at: str) -> str:
    normalized = captured_at.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    return f"{category_id}__{dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _field(product: Any, name: str, default: Any = None) -> Any:
    if isinstance(product, dict):
        return product.get(name, default)
    return getattr(product, name, default)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _product_name(product: Any) -> str | None:
    for field in ("raw_title", "product_name", "name", "title"):
        value = _field(product, field)
        if value:
            return _clean_text(value)
    return None


def _normalize_bucket_label(dimension: SortimentDimension, value: Any) -> str:
    cleaned = _clean_text(value)
    if not cleaned or cleaned.casefold() in DIRTY_BUCKET_VALUES:
        return NOT_INFORMED_LABEL
    if dimension == "available_sizes":
        return cleaned.upper()
    return cleaned.casefold()


def _raw_dimension_values(dimension: SortimentDimension, product: Any) -> list[Any]:
    raw_value = _field(product, dimension)
    if raw_value is None:
        return []
    if dimension in {"available_colors", "available_sizes"}:
        if isinstance(raw_value, str):
            return [part for part in re.split(r"[,;|]", raw_value)]
        if isinstance(raw_value, (list, tuple, set)):
            return list(raw_value)
        return [raw_value]
    return [raw_value]


def _dimension_labels_for_product(
    dimension: SortimentDimension,
    product: Any,
) -> list[str]:
    labels = []
    seen = set()
    for raw_value in _raw_dimension_values(dimension, product):
        label = _normalize_bucket_label(dimension, raw_value)
        if label == NOT_INFORMED_LABEL:
            continue
        if label in seen:
            continue
        labels.append(label)
        seen.add(label)
    return labels or [NOT_INFORMED_LABEL]


def _build_evidence(product: Any) -> SortimentBucketEvidence:
    return SortimentBucketEvidence(
        scan_product_id=str(_field(product, "scan_product_id")),
        product_name=_product_name(product),
        url=_field(product, "url"),
    )


def _aggregate_dimension(
    dimension: SortimentDimension,
    products: Iterable[Any],
    evidence_limit: int,
) -> SortimentDimensionSnapshot:
    counts: dict[str, int] = defaultdict(int)
    evidence: dict[str, list[SortimentBucketEvidence]] = defaultdict(list)

    for product in products:
        labels = _dimension_labels_for_product(dimension, product)
        product_evidence = _build_evidence(product)
        for label in labels:
            counts[label] += 1
            if len(evidence[label]) < evidence_limit:
                evidence[label].append(product_evidence)

    buckets = [
        SortimentBucketSnapshot(
            label=label,
            count=count,
            evidence=evidence[label],
        )
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return SortimentDimensionSnapshot(dimension=dimension, buckets=buckets)


def _aggregate_snapshot_dimensions(
    products: Iterable[Any],
    evidence_limit: int,
) -> list[SortimentDimensionSnapshot]:
    product_list = list(products)
    return [
        _aggregate_dimension(dimension, product_list, evidence_limit)
        for dimension in SORTIMENT_DIMENSIONS
    ]


def _dimension_bucket_map(
    dimension: SortimentDimensionSnapshot | None,
) -> dict[str, SortimentBucketSnapshot]:
    if dimension is None:
        return {}
    return {bucket.label: bucket for bucket in dimension.buckets}


def _build_deltas(
    latest: SortimentDimensionSnapshot,
    previous: SortimentDimensionSnapshot | None,
) -> list[SortimentBucketDelta]:
    previous_buckets = _dimension_bucket_map(previous)
    labels = set(previous_buckets)
    labels.update(bucket.label for bucket in latest.buckets)

    deltas: list[SortimentBucketDelta] = []
    for label in sorted(labels):
        latest_bucket = next(
            (bucket for bucket in latest.buckets if bucket.label == label),
            None,
        )
        previous_bucket = previous_buckets.get(label)
        latest_count = latest_bucket.count if latest_bucket else 0
        previous_count = previous_bucket.count if previous_bucket else 0
        delta_abs = latest_count - previous_count
        delta_pct = None
        if previous_count > 0:
            delta_pct = round((delta_abs / previous_count) * 100, 2)
        deltas.append(
            SortimentBucketDelta(
                label=label,
                latest_count=latest_count,
                previous_count=previous_count,
                delta_abs=delta_abs,
                delta_pct=delta_pct,
                evidence=latest_bucket.evidence if latest_bucket else [],
            )
        )

    return sorted(deltas, key=lambda bucket: (-abs(bucket.delta_abs), bucket.label))


async def run_sortiment_category(category_id: str) -> SortimentCategorySnapshot:
    category = get_sortiment_category(category_id)
    if category is None:
        raise ValueError(f"Sortiment category not found: {category_id}")

    engine = engine_factory.get_engine(category.brand)
    captured_at = _now_iso()
    snapshot_id = _snapshot_id(category.id, captured_at)
    max_products = max(1, int(settings.SORTIMENT_MAX_PRODUCTS_PER_CATEGORY))
    evidence_limit = max(1, int(settings.SORTIMENT_EVIDENCE_PER_BUCKET))

    scraped_products: list[Any] = []
    async for product in engine.run_bulk_scrape(category_url=category.url):
        scraped_products.append(product)
        if len(scraped_products) >= max_products:
            break

    enriched_products = ensure_scan_product_ids(
        scraped_products,
        brand=category.brand,
        scan_id=snapshot_id,
    )
    snapshot = SortimentCategorySnapshot(
        snapshot_id=snapshot_id,
        category_id=category.id,
        source_monitor_id=category.source_monitor_id,
        brand=category.brand,
        url=category.url,
        captured_at=captured_at,
        product_count=len(enriched_products),
        dimensions=_aggregate_snapshot_dimensions(enriched_products, evidence_limit),
    )
    persist_sortiment_snapshot(snapshot)
    update_sortiment_category(category.id, last_snapshot_at=captured_at)
    return snapshot


async def try_run_sortiment_category(
    category_id: str,
) -> tuple[str, SortimentCategorySnapshot | None]:
    if SORTIMENT_RUN_GUARD.locked():
        return ("busy", None)

    async with SORTIMENT_RUN_GUARD:
        snapshot = await run_sortiment_category(category_id)
        return ("completed", snapshot)


async def run_enabled_sortiment_job() -> str:
    if SORTIMENT_RUN_GUARD.locked():
        return "busy"

    async with SORTIMENT_RUN_GUARD:
        for category in load_sortiment_categories(enabled_only=True):
            await run_sortiment_category(category.id)
    return "completed"


def get_sortiment_dashboard(category_id: str) -> SortimentDashboardResponse:
    category = get_sortiment_category(category_id)
    if category is None:
        raise ValueError(f"Sortiment category not found: {category_id}")

    manifest = load_sortiment_manifest(category_id)
    if manifest is None or not manifest.latest_snapshot:
        raise ValueError(f"Sortiment snapshot not found: {category_id}")

    latest_snapshot = load_sortiment_snapshot(manifest.latest_snapshot)
    if latest_snapshot is None:
        raise ValueError(f"Sortiment latest snapshot missing: {category_id}")

    previous_snapshot = None
    if manifest.previous_snapshot:
        previous_snapshot = load_sortiment_snapshot(manifest.previous_snapshot)

    previous_dimensions = {
        dimension.dimension: dimension
        for dimension in (previous_snapshot.dimensions if previous_snapshot else [])
    }

    dimensions = [
        SortimentDashboardDimension(
            dimension=dimension.dimension,
            current_distribution=dimension.buckets,
            deltas=[]
            if previous_snapshot is None
            else _build_deltas(
                dimension,
                previous_dimensions.get(dimension.dimension),
            ),
        )
        for dimension in latest_snapshot.dimensions
    ]

    refreshed_category: SortimentCategoryRow = (
        get_sortiment_category(category_id) or category
    )
    return SortimentDashboardResponse(
        category=refreshed_category,
        baseline=previous_snapshot is None,
        latest_snapshot=manifest.latest_snapshot,
        previous_snapshot=manifest.previous_snapshot,
        latest_snapshot_at=manifest.latest_snapshot_at,
        previous_snapshot_at=manifest.previous_snapshot_at,
        dimensions=dimensions,
    )
