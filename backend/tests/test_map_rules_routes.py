from pathlib import Path

from fastapi.testclient import TestClient

from app import app
import api.routes_map_rules as routes_map_rules
from services.map_rules_service import MapRuleService


def _client_with_temp_rules(monkeypatch, tmp_path: Path) -> TestClient:
    service = MapRuleService(tmp_path / "map_rules.json")
    monkeypatch.setattr(routes_map_rules, "map_rules_service", service)
    return TestClient(app)


def test_list_returns_empty_array_when_no_rules(monkeypatch, tmp_path):
    client = _client_with_temp_rules(monkeypatch, tmp_path)

    response = client.get("/map-rules", headers={"X-API-Key": "dev-api-key"})

    assert response.status_code == 200
    assert response.json() == []


def test_create_persists_valid_rule_and_rejects_invalid_scope(monkeypatch, tmp_path):
    client = _client_with_temp_rules(monkeypatch, tmp_path)

    response = client.post(
        "/map-rules",
        headers={"X-API-Key": "dev-api-key"},
        json={
            "scope": "brand",
            "target": "Aramis",
            "min_price": 299.9,
            "notes": "Polo base",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["brand"] == "Aramis"

    listed = client.get("/map-rules", headers={"X-API-Key": "dev-api-key"}).json()
    assert listed[0]["id"] == body["id"]

    invalid = client.post(
        "/map-rules",
        headers={"X-API-Key": "dev-api-key"},
        json={"scope": "store", "target": "Aramis", "min_price": 299.9},
    )
    assert invalid.status_code == 422


def test_update_mutates_existing_rule_and_404s_unknown(monkeypatch, tmp_path):
    client = _client_with_temp_rules(monkeypatch, tmp_path)
    created = client.post(
        "/map-rules",
        headers={"X-API-Key": "dev-api-key"},
        json={"scope": "category", "target": "Camisas", "brand": "Aramis", "min_price": 199.9},
    ).json()

    response = client.patch(
        f"/map-rules/{created['id']}",
        headers={"X-API-Key": "dev-api-key"},
        json={"min_price": 249.9, "active": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["min_price"] == 249.9
    assert body["active"] is False

    missing = client.patch(
        "/map-rules/missing",
        headers={"X-API-Key": "dev-api-key"},
        json={"min_price": 249.9},
    )
    assert missing.status_code == 404


def test_delete_removes_existing_rule_and_404s_unknown(monkeypatch, tmp_path):
    client = _client_with_temp_rules(monkeypatch, tmp_path)
    created = client.post(
        "/map-rules",
        headers={"X-API-Key": "dev-api-key"},
        json={"scope": "product", "target": "SKU-1", "min_price": 99.9},
    ).json()

    response = client.delete(
        f"/map-rules/{created['id']}",
        headers={"X-API-Key": "dev-api-key"},
    )

    assert response.status_code == 204
    assert client.get("/map-rules", headers={"X-API-Key": "dev-api-key"}).json() == []

    missing = client.delete("/map-rules/missing", headers={"X-API-Key": "dev-api-key"})
    assert missing.status_code == 404
