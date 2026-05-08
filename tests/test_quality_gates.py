import pytest
from core.models import RawProductBronze
from pydantic import ValidationError
from services.engines.vtex_engine import VTEXEngine

def test_raw_product_validation_success():
    """Testa se um produto válido passa pela validação."""
    data = {
        "url": "https://example.com/p",
        "brand": "BrandX",
        "raw_title": "Produto Teste",
        "raw_description": "Descrição",
        "price_full": 100.0,
        "image_url": "https://example.com/img.jpg"
    }
    prod = RawProductBronze.model_validate(data)
    assert prod.raw_title == "Produto Teste"
    assert prod.price_full == 100.0

def test_raw_product_validation_zero_price():
    """Testa se preço zero lança erro."""
    data = {
        "url": "https://example.com/p",
        "brand": "BrandX",
        "raw_title": "Produto Teste",
        "raw_description": "Descrição",
        "price_full": 0.0,
        "image_url": "https://example.com/img.jpg"
    }
    with pytest.raises(ValidationError) as exc:
        RawProductBronze.model_validate(data)
    assert "Preço zerado ou negativo" in str(exc.value)

def test_raw_product_validation_missing_image():
    """Testa se imagem ausente lança erro."""
    data = {
        "url": "https://example.com/p",
        "brand": "BrandX",
        "raw_title": "Produto Teste",
        "raw_description": "Descrição",
        "price_full": 100.0,
        "image_url": None
    }
    with pytest.raises(ValidationError) as exc:
        RawProductBronze.model_validate(data)
    assert "URL da imagem ausente ou inválida" in str(exc.value)

def test_engine_filter_results():
    """Testa o filtro do engine descartando itens inválidos."""
    engine = VTEXEngine(brand_key="teste")
    products = [
        # Válido
        {
            "url": "https://example.com/1",
            "brand": "BrandX",
            "raw_title": "Válido",
            "raw_description": "Desc",
            "price_full": 50.0,
            "image_url": "img.jpg"
        },
        # Inválido (preço zero)
        {
            "url": "https://example.com/2",
            "brand": "BrandX",
            "raw_title": "Preço Zero",
            "raw_description": "Desc",
            "price_full": 0.0,
            "image_url": "img.jpg"
        },
        # Inválido (sem imagem)
        {
            "url": "https://example.com/3",
            "brand": "BrandX",
            "raw_title": "Sem Imagem",
            "raw_description": "Desc",
            "price_full": 10.0,
            "image_url": ""
        }
    ]
    
    # Mock log_callback to avoid errors
    logs = []
    def mock_log(payload): 
        if isinstance(payload, dict):
            logs.append(payload.get("message", ""))
        else:
            logs.append(str(payload))
    
    filtered = engine.validate_and_filter(products, log_callback=mock_log)
    
    assert len(filtered) == 1
    assert filtered[0]["raw_title"] == "Válido"
    assert any("Preço Zero" in l for l in logs)
    assert any("Sem Imagem" in l for l in logs)
