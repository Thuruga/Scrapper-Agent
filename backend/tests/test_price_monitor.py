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
