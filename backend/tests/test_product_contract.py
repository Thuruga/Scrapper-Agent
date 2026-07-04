from services.product_contract import (
    CANONICAL_PRODUCT_COLUMNS,
    build_canonical_product_row,
    normalize_specifications_aliases,
)


def test_canonical_columns_match_phase_37_contract():
    assert CANONICAL_PRODUCT_COLUMNS == [
        "brand",
        "url",
        "price_full",
        "price_discount",
        "product_name",
        "product_description",
        "composition",
        "available_colors",
        "available_sizes",
        "product_code",
        "category",
        "rating",
        "review_count",
    ]


def test_build_canonical_product_row():
    row = build_canonical_product_row(
        {
            "brand": "Aramis",
            "url": "https://www.aramis.com.br/p/camisa",
            "raw_title": "Camisa Linho",
            "raw_description": "Camisa em linho leve.",
            "price_full": 299.9,
            "available_colors": ["Azul", "Branco"],
            "available_sizes": ["M", "G"],
            "specifications": {
                "Composição do produto": "100% Linho",
            },
        }
    )

    assert list(row.keys()) == CANONICAL_PRODUCT_COLUMNS
    assert row["product_name"] == "Camisa Linho"
    assert row["product_description"] == "Camisa em linho leve."
    assert row["composition"] == "100% Linho"
    assert row["available_colors"] == ["Azul", "Branco"]
    assert row["available_sizes"] == ["M", "G"]
    assert row["product_code"] is None
    assert row["category"] is None
    assert row["rating"] is None
    assert row["review_count"] is None


def test_build_canonical_product_row_normalizes_delta_discount_prices():
    row = build_canonical_product_row(
        {
            "brand": "Aramis",
            "url": "https://www.aramis.com.br/p/camisa-polo",
            "raw_title": "Camisa Polo",
            "price_full": 199.9,
            "price_discount": 100.0,
            "price_discount_is_delta": True,
        }
    )

    assert row["price_full"] == 299.9
    assert row["price_discount"] == 199.9


def test_aliases_are_additive():
    normalized = normalize_specifications_aliases(
        {
            "Composição do produto": "100% Algodão",
            "Referência": "REF-123",
        }
    )

    assert normalized["Composição do produto"] == "100% Algodão"
    assert normalized["Referência"] == "REF-123"
    assert normalized["composition"] == "100% Algodão"
    assert normalized["product_code"] == "REF-123"
