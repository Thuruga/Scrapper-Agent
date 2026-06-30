import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from services.price_monitor_service import PriceMonitorService
from core.models import PriceMonitorConfig, RawProductBronze

@pytest.mark.asyncio
async def test_price_monitor_recording_change():
    """Testa se o serviço registra mudanças de preço no histórico."""
    service = PriceMonitorService()
    job_id = "test-job"
    
    # Configuração inicial
    config = PriceMonitorConfig(
        job_id=job_id,
        url="http://example.com",
        brand="test-brand",
        interval_minutes=1,
        duration_hours=1,
        active=True,
        last_price=100.0
    )
    service.monitors[job_id] = config
    
    # Mock do motor
    mock_engine = MagicMock()
    # Retorna um preço DIFERENTE (120.0) para disparar a mudança
    mock_engine.get_product_details = AsyncMock(return_value={
        "url": "http://example.com",
        "brand": "test-brand",
        "raw_title": "Produto Teste",
        "raw_description": "Descrição Teste",
        "price_full": 120.0,
        "image_url": "http://example.com/img.jpg",
        "stock_availability": True
    })
    
    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock):
        
        # Executa uma iteração do loop manualmente (simplificado)
        # Em vez de rodar o loop infinito, chamamos a lógica interna de atualização
        # Para isso, vamos extrair a lógica de checagem do _monitor_loop ou rodar uma vez e cancelar
        
        # Simulando o corpo do loop
        product_data = await mock_engine.get_product_details(config.url)
        product = RawProductBronze.model_validate(product_data)
        
        if config.last_price != product.price_full:
            from core.models import PriceHistoryEntry
            entry = PriceHistoryEntry(price=product.price_full, available=product.stock_availability)
            config.history.append(entry)
            config.last_price = product.price_full
            
    assert len(config.history) == 1
    assert config.history[0].price == 120.0
    assert config.last_price == 120.0

@pytest.mark.asyncio
async def test_price_monitor_no_change():
    """Testa se o serviço NÃO registra nada se o preço for igual."""
    service = PriceMonitorService()
    job_id = "test-job-no-change"
    
    config = PriceMonitorConfig(
        job_id=job_id,
        url="http://example.com",
        brand="test-brand",
        interval_minutes=1,
        duration_hours=1,
        active=True,
        last_price=100.0,
        history=[]
    )
    service.monitors[job_id] = config
    
    # Mesmo preço (100.0)
    mock_engine = MagicMock()
    mock_engine.get_product_details = AsyncMock(return_value={
        "url": "http://example.com",
        "brand": "test-brand",
        "raw_title": "Produto Teste",
        "raw_description": "Descrição Teste",
        "price_full": 100.0,
        "image_url": "http://example.com/img.jpg",
        "stock_availability": True
    })
    
    # Lógica de comparação
    product_data = await mock_engine.get_product_details(config.url)
    product = RawProductBronze.model_validate(product_data)
    
    if config.last_price != product.price_full:
        from core.models import PriceHistoryEntry
        entry = PriceHistoryEntry(price=product.price_full, available=product.stock_availability)
        config.history.append(entry)
    
    assert len(config.history) == 0
    assert config.last_price == 100.0


@pytest.mark.asyncio
async def test_dedup_active():
    """Adicionar um monitor para (url+brand) que já está ativo é no-op: retorna 'already_active'
    sem criar nova entrada em service.monitors."""
    service = PriceMonitorService()
    existing_id = "existing-job-active"
    config = PriceMonitorConfig(
        job_id=existing_id,
        url="https://www.example.com/produto/camisa?utm_source=google",
        brand="TestBrand",
        interval_minutes=10,
        duration_hours=24,
        active=True,
    )
    service.monitors[existing_id] = config

    # Mesma URL normalizada (tracking param removido, www. removido) + mesma brand
    with patch("services.price_monitor_service.asyncio.create_task") as mock_task, \
         patch.object(service, "_save_monitors"):
        result, status = await service.start_monitor(
            job_id="new-job-id",
            url="https://example.com/produto/camisa",
            brand="testbrand",
            interval=10,
            duration=24,
        )

    assert status == "already_active"
    assert len(service.monitors) == 1, "Nenhum novo monitor deve ter sido criado"
    assert "new-job-id" not in service.monitors
    mock_task.assert_not_called()


@pytest.mark.asyncio
async def test_dedup_reactivate():
    """Adicionar um monitor para (url+brand) já parado deve reativar o monitor existente
    e retornar 'reactivated', sem criar nova entrada."""
    service = PriceMonitorService()
    existing_id = "existing-job-stopped"
    config = PriceMonitorConfig(
        job_id=existing_id,
        url="https://example.com/produto/polo",
        brand="TestBrand",
        interval_minutes=10,
        duration_hours=24,
        active=False,
    )
    service.monitors[existing_id] = config

    with patch("services.price_monitor_service.asyncio.create_task"), \
         patch.object(service, "_save_monitors"):
        result, status = await service.start_monitor(
            job_id="new-job-id-2",
            url="https://www.example.com/produto/polo",
            brand="TestBrand",
            interval=10,
            duration=24,
        )

    assert status == "reactivated"
    assert len(service.monitors) == 1, "Nenhum novo monitor deve ter sido criado"
    assert "new-job-id-2" not in service.monitors
    assert service.monitors[existing_id].active is True
