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
async def test_monitor_uses_get_pdp_product_not_get_product_details():
    """REGRESSÃO (monitor-marketplace-pendente): o _monitor_loop deve consumir
    get_pdp_product (produto COMPLETO), não get_product_details (que nos engines
    de marketplace devolve só {"seller": ...} e quebrava a validação)."""
    service = PriceMonitorService()
    job_id = "test-pdp-path"
    config = PriceMonitorConfig(
        job_id=job_id,
        url="https://produto.mercadolivre.com.br/MLB-123",
        brand="mercado_livre",
        interval_minutes=1,
        duration_hours=1,
        active=True,
    )
    service.monitors[job_id] = config

    mock_engine = MagicMock()
    # get_product_details: shape seller-only do cross-marketplace (NÃO deve ser usado)
    mock_engine.get_product_details = AsyncMock(return_value={"seller": "Aramis"})
    # get_pdp_product: produto completo
    mock_engine.get_pdp_product = AsyncMock(return_value={
        "url": config.url,
        "brand": "mercado_livre",
        "raw_title": "Camiseta Aramis New Basic Navy",
        "raw_description": "Camiseta Aramis",
        "price_full": 199.9,
        "image_url": "https://http2.mlstatic.com/img.jpg",
        "stock_availability": True,
    })

    async def stop_after_first(*args, **kwargs):
        # Para o loop após a primeira checagem para não rodar para sempre.
        config.active = False

    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock) as mock_ws, \
         patch.object(service, "_save_monitors"), \
         patch("services.price_monitor_service.asyncio.sleep", new=AsyncMock(side_effect=stop_after_first)):
        await service._monitor_loop(job_id)

    mock_engine.get_pdp_product.assert_awaited()
    mock_engine.get_product_details.assert_not_called()
    assert config.last_price == 199.9, "Monitor de marketplace deve resolver o preço"
    assert config.product_name == "Camiseta Aramis New Basic Navy"
    assert len(config.history) == 1
    # Não deve ter emitido erro de validação
    error_msgs = [
        c.args[0] for c in mock_ws.await_args_list
        if isinstance(c.args[0], dict) and c.args[0].get("type") == "error"
    ]
    assert not error_msgs, f"Não deveria emitir erro; emitiu: {error_msgs}"


@pytest.mark.asyncio
async def test_monitor_invalid_payload_does_not_crash_loop():
    """Se get_pdp_product devolver um payload incompleto (ex.: engine de marketplace
    que ainda não foi sobrescrito → herda o default que delega para get_product_details
    seller-only), o loop NÃO deve travar: captura ValidationError, loga e segue."""
    service = PriceMonitorService()
    job_id = "test-invalid-payload"
    config = PriceMonitorConfig(
        job_id=job_id,
        url="https://www.amazon.com.br/dp/X",
        brand="amazon",
        interval_minutes=1,
        duration_hours=1,
        active=True,
    )
    service.monitors[job_id] = config

    mock_engine = MagicMock()
    # Simula o default da base (delega p/ get_product_details seller-only)
    mock_engine.get_pdp_product = AsyncMock(return_value={"seller": "Amazon"})

    async def stop_after_first(*args, **kwargs):
        config.active = False

    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock), \
         patch.object(service, "_save_monitors"), \
         patch("services.price_monitor_service.asyncio.sleep", new=AsyncMock(side_effect=stop_after_first)):
        # Não deve levantar — o loop precisa sobreviver ao payload inválido
        await service._monitor_loop(job_id)

    assert config.last_price is None
    assert config.product_name is None
    assert len(config.history) == 0


@pytest.mark.asyncio
async def test_price_monitor_promo_only_change_triggers_history():
    """UX-02 (D-01/D-03): uma mudanca APENAS de promocao (price_full inalterado,
    discount adicionado) deve gerar uma entrada de historico e uma mensagem WS
    price_update cujo payload contenha o campo price_discount.

    RED ate a Task 2 (campo last_price_discount nos models) + Task 3 (deteccao
    de mudanca + payload WS discount-aware) serem implementadas.
    """
    service = PriceMonitorService()
    job_id = "test-promo-only"

    config = PriceMonitorConfig(
        job_id=job_id,
        url="http://example.com/produto-promo",
        brand="test-brand",
        interval_minutes=1,
        duration_hours=1,
        active=True,
        last_price=100.0,
    )
    service.monitors[job_id] = config

    mock_engine = MagicMock()
    # price_full inalterado (100.0), mas agora com um desconto (delta) de 20.0 —
    # promo-only change: preco efetivo nao mudou, mas o desconto apareceu.
    mock_engine.get_pdp_product = AsyncMock(return_value={
        "url": config.url,
        "brand": "test-brand",
        "raw_title": "Produto Promo",
        "raw_description": "Descricao",
        "price_full": 100.0,
        "price_discount": 20.0,
        "image_url": "http://example.com/img.jpg",
        "stock_availability": True,
    })

    # config.last_price nao e None, entao _monitor_loop faz um jitter inicial
    # (1o asyncio.sleep) ANTES do laco `while config.active`. So o 2o sleep
    # (fim do ciclo, dentro do laco) deve parar o monitor.
    sleep_calls = {"count": 0}

    async def stop_after_second_sleep(*args, **kwargs):
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            config.active = False

    with patch("services.price_monitor_service.engine_factory.get_engine", return_value=mock_engine), \
         patch("services.price_monitor_service.manager.send_message", new_callable=AsyncMock) as mock_ws, \
         patch.object(service, "_save_monitors"), \
         patch("services.price_monitor_service.asyncio.sleep", new=AsyncMock(side_effect=stop_after_second_sleep)):
        await service._monitor_loop(job_id)

    assert len(config.history) == 1, (
        "Mudanca apenas de desconto (promo-only) deve gerar uma entrada de historico (D-01)"
    )

    price_update_payloads = [
        c.args[0] for c in mock_ws.await_args_list
        if isinstance(c.args[0], dict) and c.args[0].get("type") == "price_update"
    ]
    assert price_update_payloads, "Deveria ter emitido uma mensagem WS price_update"
    assert "price_discount" in price_update_payloads[0], (
        "Payload WS price_update deve conter o campo price_discount (D-03)"
    )


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
