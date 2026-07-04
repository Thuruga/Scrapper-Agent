from pathlib import Path

import pytest

from core.models import MapRule, SearchProductResult
from services.map_rules_service import MapRuleService, find_applicable_rule, normalize_url


def test_old_search_payload_validates_with_phase43_defaults():
    product = SearchProductResult(
        brand="Aramis",
        product_name="Camisa",
        url="https://www.aramis.com.br/p/camisa",
        price_full=199.9,
    )

    assert product.promotions == []
    assert product.map_violation is False
    assert product.map_price_floor is None


def test_map_rule_rejects_invalid_scope():
    with pytest.raises(Exception):
        MapRule(scope="store", target="Aramis", min_price=100)  # type: ignore[arg-type]


def test_service_missing_or_empty_file_returns_empty(tmp_path: Path):
    service = MapRuleService(tmp_path / "map_rules.json")
    assert service.list_rules() == []

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert MapRuleService(empty_file).list_rules() == []


def test_create_update_delete_persists_atomically(tmp_path: Path):
    db_file = tmp_path / "map_rules.json"
    service = MapRuleService(db_file)

    created = service.create_rule(
        {"scope": "brand", "target": "Aramis", "min_price": 299.9, "notes": "base"}
    )
    assert db_file.exists()
    assert not db_file.with_suffix(".json.tmp").exists()
    assert MapRuleService(db_file).get_rule(created.id).min_price == 299.9

    updated = service.update_rule(created.id, {"min_price": 319.9, "active": False})
    assert updated is not None
    assert updated.min_price == 319.9
    assert updated.active is False

    assert service.delete_rule(created.id) is True
    assert service.list_rules() == []
    assert service.delete_rule(created.id) is False


def test_applicable_rule_precedence_product_category_brand():
    rules = [
        MapRule(scope="brand", target="Aramis", min_price=100),
        MapRule(scope="category", target="Camisas", brand="Aramis", min_price=150),
        MapRule(scope="product", target="CAM-123", min_price=200),
    ]
    product = {
        "brand": "Aramis",
        "category": "Camisas",
        "product_code": "CAM-123",
        "url": "https://www.aramis.com.br/p/camisa",
    }

    assert find_applicable_rule(product, rules).scope == "product"

    assert find_applicable_rule({**product, "product_code": "OUTRO"}, rules).scope == "category"
    assert find_applicable_rule({**product, "product_code": "OUTRO", "category": "Polos"}, rules).scope == "brand"


def test_product_rule_matches_normalized_url_when_code_absent():
    rule = MapRule(
        scope="product",
        target="https://www.aramis.com.br/p/camisa?utm=x",
        min_price=199.0,
    )
    product = {"brand": "Aramis", "url": "https://aramis.com.br/p/camisa/"}

    assert normalize_url(rule.target) == "aramis.com.br/p/camisa"
    assert find_applicable_rule(product, [rule]) == rule
