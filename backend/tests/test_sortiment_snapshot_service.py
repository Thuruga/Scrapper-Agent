import asyncio

from core.models import SortimentCategoryRow


class _FakeSortimentEngine:
    def __init__(self, products):
        self.products = products

    async def run_bulk_scrape(self, category_url: str, **kwargs):
        for product in self.products:
            yield product


def _configure_sortiment_paths(tmp_path, monkeypatch):
    import services.sortiment_artifact_service as sortiment_artifact_service
    import services.sortiment_registry_service as sortiment_registry_service

    monitored_file = tmp_path / "monitored_categories.json"
    registry_file = tmp_path / "sortiment_categories.json"

    monkeypatch.setattr(sortiment_registry_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(sortiment_registry_service, "MONITORS_FILE", monitored_file)
    monkeypatch.setattr(
        sortiment_registry_service,
        "SORTIMENT_REGISTRY_FILE",
        registry_file,
    )
    monkeypatch.setattr(sortiment_artifact_service, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        sortiment_artifact_service,
        "SORTIMENT_SNAPSHOT_DIR",
        tmp_path / "sortiment_snapshots",
    )
    monkeypatch.setattr(
        sortiment_artifact_service,
        "SORTIMENT_MANIFEST_DIR",
        tmp_path / "sortiment_manifests",
    )


def test_run_sortiment_category_persists_single_snapshot_and_manifest(
    tmp_path, monkeypatch
):
    import services.sortiment_artifact_service as sortiment_artifact_service
    import services.sortiment_registry_service as sortiment_registry_service
    import services.sortiment_snapshot_service as sortiment_snapshot_service
    from services.engines import factory

    _configure_sortiment_paths(tmp_path, monkeypatch)
    sortiment_registry_service.save_sortiment_categories(
        [
            SortimentCategoryRow(
                id="sortiment-1",
                source_monitor_id="monitor-1",
                brand="aramis",
                url="https://www.aramis.com.br/polos",
                enabled=True,
            )
        ]
    )
    engine = _FakeSortimentEngine(
        [
            {
                "url": "https://example.com/polo-azul",
                "brand": "aramis",
                "raw_title": "Polo Azul",
                "available_colors": ["Azul"],
                "available_sizes": ["M"],
                "composition": "100% Algodao",
            },
            {
                "url": "https://example.com/polo-branco",
                "brand": "aramis",
                "raw_title": "Polo Branco",
                "available_colors": ["Branco"],
                "available_sizes": ["G"],
                "composition": "100% Algodao",
            },
        ]
    )

    monkeypatch.setattr(factory.engine_factory, "get_engine", lambda brand: engine)
    monkeypatch.setattr(
        sortiment_snapshot_service,
        "_now_iso",
        lambda: "2026-07-06T03:00:00Z",
    )
    monkeypatch.setattr(
        sortiment_snapshot_service.settings,
        "SORTIMENT_MAX_PRODUCTS_PER_CATEGORY",
        1000,
    )
    monkeypatch.setattr(
        sortiment_snapshot_service.settings,
        "SORTIMENT_EVIDENCE_PER_BUCKET",
        2,
    )

    snapshot = asyncio.run(
        sortiment_snapshot_service.run_sortiment_category("sortiment-1")
    )

    manifest = sortiment_artifact_service.load_sortiment_manifest("sortiment-1")
    snapshot_files = list((tmp_path / "sortiment_snapshots").glob("*.json"))

    assert snapshot.category_id == "sortiment-1"
    assert snapshot.product_count == 2
    assert len(snapshot_files) == 1
    assert manifest is not None
    assert manifest.latest_snapshot == "sortiment-1__20260706T030000Z.json"
    assert manifest.previous_snapshot is None


def test_sortiment_aggregation_normalizes_missing_dirty_values_without_cartesian_buckets(
    tmp_path, monkeypatch
):
    import services.sortiment_registry_service as sortiment_registry_service
    import services.sortiment_snapshot_service as sortiment_snapshot_service
    from services.engines import factory

    _configure_sortiment_paths(tmp_path, monkeypatch)
    sortiment_registry_service.save_sortiment_categories(
        [
            SortimentCategoryRow(
                id="sortiment-1",
                source_monitor_id="monitor-1",
                brand="aramis",
                url="https://www.aramis.com.br/polos",
                enabled=True,
            )
        ]
    )
    engine = _FakeSortimentEngine(
        [
            {
                "url": "https://example.com/polo-azul",
                "brand": "aramis",
                "raw_title": "Polo Azul",
                "available_colors": [" Azul ", " "],
                "available_sizes": ["M", " "],
                "composition": " 100% Algodao ",
            },
            {
                "url": "https://example.com/polo-vazio",
                "brand": "aramis",
                "raw_title": "Polo Sem Dados",
                "available_colors": [],
                "available_sizes": None,
                "composition": "-",
            },
            {
                "url": "https://example.com/polo-misto",
                "brand": "aramis",
                "raw_title": "Polo Misto",
                "available_colors": "azul, branco",
                "available_sizes": "g, M",
                "composition": None,
            },
        ]
    )

    monkeypatch.setattr(factory.engine_factory, "get_engine", lambda brand: engine)
    monkeypatch.setattr(
        sortiment_snapshot_service,
        "_now_iso",
        lambda: "2026-07-06T03:10:00Z",
    )
    monkeypatch.setattr(
        sortiment_snapshot_service.settings,
        "SORTIMENT_EVIDENCE_PER_BUCKET",
        2,
    )

    snapshot = asyncio.run(
        sortiment_snapshot_service.run_sortiment_category("sortiment-1")
    )
    dimensions = {
        dimension.dimension: {
            bucket.label: bucket.count for bucket in dimension.buckets
        }
        for dimension in snapshot.dimensions
    }

    assert set(dimensions) == {
        "available_colors",
        "available_sizes",
        "composition",
    }
    assert dimensions["available_colors"]["azul"] == 2
    assert dimensions["available_colors"]["branco"] == 1
    assert dimensions["available_colors"]["não informado"] == 1
    assert dimensions["available_sizes"]["M"] == 2
    assert dimensions["available_sizes"]["G"] == 1
    assert dimensions["available_sizes"]["não informado"] == 1
    assert dimensions["composition"]["100% algodao"] == 1
    assert dimensions["composition"]["não informado"] == 2
    assert not any("|" in label for label in dimensions["available_colors"])


def test_sortiment_dashboard_marks_baseline_then_computes_deltas(
    tmp_path, monkeypatch
):
    import services.sortiment_registry_service as sortiment_registry_service
    import services.sortiment_snapshot_service as sortiment_snapshot_service
    from services.engines import factory

    _configure_sortiment_paths(tmp_path, monkeypatch)
    sortiment_registry_service.save_sortiment_categories(
        [
            SortimentCategoryRow(
                id="sortiment-1",
                source_monitor_id="monitor-1",
                brand="aramis",
                url="https://www.aramis.com.br/polos",
                enabled=True,
            )
        ]
    )
    engine = _FakeSortimentEngine(
        [
            {
                "url": "https://example.com/polo-azul",
                "brand": "aramis",
                "raw_title": "Polo Azul",
                "available_colors": ["Azul"],
                "available_sizes": ["M"],
                "composition": "100% Algodao",
            },
            {
                "url": "https://example.com/polo-preto",
                "brand": "aramis",
                "raw_title": "Polo Preto",
                "available_colors": ["Preto"],
                "available_sizes": ["G"],
                "composition": "Linho",
            },
        ]
    )
    times = iter(["2026-07-06T04:00:00Z", "2026-07-06T05:00:00Z"])

    monkeypatch.setattr(factory.engine_factory, "get_engine", lambda brand: engine)
    monkeypatch.setattr(sortiment_snapshot_service, "_now_iso", lambda: next(times))
    monkeypatch.setattr(
        sortiment_snapshot_service.settings,
        "SORTIMENT_EVIDENCE_PER_BUCKET",
        2,
    )

    asyncio.run(sortiment_snapshot_service.run_sortiment_category("sortiment-1"))
    baseline = sortiment_snapshot_service.get_sortiment_dashboard("sortiment-1")

    assert baseline.baseline is True
    assert baseline.previous_snapshot_at is None
    assert baseline.latest_snapshot_at == "2026-07-06T04:00:00Z"

    engine.products = [
        {
            "url": "https://example.com/polo-azul",
            "brand": "aramis",
            "raw_title": "Polo Azul",
            "available_colors": ["Azul"],
            "available_sizes": ["M"],
            "composition": "100% Algodao",
        },
        {
            "url": "https://example.com/polo-azul-2",
            "brand": "aramis",
            "raw_title": "Polo Azul 2",
            "available_colors": ["Azul"],
            "available_sizes": ["M"],
            "composition": "100% Algodao",
        },
        {
            "url": "https://example.com/polo-branco",
            "brand": "aramis",
            "raw_title": "Polo Branco",
            "available_colors": ["Branco"],
            "available_sizes": ["G"],
            "composition": "Linho",
        },
    ]

    asyncio.run(sortiment_snapshot_service.run_sortiment_category("sortiment-1"))
    dashboard = sortiment_snapshot_service.get_sortiment_dashboard("sortiment-1")
    color_dimension = next(
        dimension
        for dimension in dashboard.dimensions
        if dimension.dimension == "available_colors"
    )
    delta_by_label = {bucket.label: bucket for bucket in color_dimension.deltas}

    assert dashboard.baseline is False
    assert dashboard.latest_snapshot_at == "2026-07-06T05:00:00Z"
    assert dashboard.previous_snapshot_at == "2026-07-06T04:00:00Z"
    assert delta_by_label["azul"].delta_abs == 1
    assert delta_by_label["azul"].delta_pct == 100.0
    assert delta_by_label["preto"].delta_abs == -1
    assert delta_by_label["preto"].delta_pct == -100.0
