"""Testes de Phase 38 Plan 01 — UX-08 backend proof.

Cobertura:
  - run_category_scan grava last_scraped_at na linha do monitor apos o scan.
    Este e o sinal de conclusao que o frontend (Plan 03) faz polling para
    detectar. O gatilho de background ja existe em routes_monitor.py
    (background_tasks.add_task(run_category_scan, row)); este teste apenas
    documenta e trava o contrato do backend — nao ha codigo de producao novo.

Toda I/O de disco e de engine e mockada (hermetico, sem rede/arquivo real).
"""
import pytest
from unittest.mock import MagicMock, patch

from services.category_monitor_service import run_category_scan


def _fake_bulk_scrape(products):
    """Retorna um async generator que produz os produtos fornecidos."""
    async def _gen(*args, **kwargs):
        for product in products:
            yield product
    return _gen


@pytest.mark.asyncio
async def test_run_category_scan_populates_last_scraped_at():
    """run_category_scan deve gravar last_scraped_at (nao nulo) na linha do
    monitor persistida via _save_local — este e o sinal de conclusao que o
    frontend faz polling para detectar (UX-08)."""
    monitor_id = "monitor-123"
    monitor_row = {
        "id": monitor_id,
        "url": "https://example.com/categoria",
        "brand": "test-brand",
        "status": "active",
    }

    fixture_products = [
        {
            "url": "https://example.com/produto-1",
            "brand": "test-brand",
            "raw_title": "Produto 1",
            "raw_description": "Descricao 1",
            "price_full": 100.0,
            "stock_availability": True,
        },
        {
            "url": "https://example.com/produto-2",
            "brand": "test-brand",
            "raw_title": "Produto 2",
            "raw_description": "Descricao 2",
            "price_full": 200.0,
            "stock_availability": False,
        },
    ]

    mock_engine = MagicMock()
    mock_engine.run_bulk_scrape = _fake_bulk_scrape(fixture_products)

    saved_data = {}

    def _fake_save_local(data):
        saved_data["value"] = data

    with patch(
        "services.engines.factory.engine_factory.get_engine",
        return_value=mock_engine,
    ), patch(
        "services.category_monitor_service._load_local",
        return_value=[dict(monitor_row)],
    ), patch(
        "services.category_monitor_service._save_local",
        side_effect=_fake_save_local,
    ), patch(
        "services.category_monitor_service.persist_monitor_stock_summary"
    ), patch(
        "services.category_monitor_service.DATA_DIR"
    ) as mock_data_dir:
        # Evita escrita real do arquivo monitored_products_{id}.json
        mock_products_file = MagicMock()
        mock_data_dir.__truediv__ = MagicMock(return_value=mock_products_file)

        await run_category_scan(monitor_row)

    assert "value" in saved_data, "_save_local deveria ter sido chamado"
    updated_rows = {item["id"]: item for item in saved_data["value"]}
    assert monitor_id in updated_rows

    updated_row = updated_rows[monitor_id]
    assert updated_row.get("last_scraped_at"), (
        "run_category_scan deve gravar last_scraped_at nao nulo na linha do monitor (UX-08)"
    )
    assert "last_stock_summary" in updated_row
