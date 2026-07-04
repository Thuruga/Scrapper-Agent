"""JSON-backed MAP rule persistence and precedence selection."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from pydantic import RootModel, ValidationError

from core.models import MapRule


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILE = DATA_DIR / "map_rules.json"


class MapRuleDatabase(RootModel):
    root: list[MapRule]


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/+$", "", parsed.path or "")
    return f"{netloc}{path}"


class MapRuleService:
    def __init__(self, db_file: Path = DB_FILE):
        self.db_file = Path(db_file)
        self.rules: list[MapRule] = []
        self.last_modified = 0.0
        self._ensure_data_dir()
        self._load_from_json()

    def _ensure_data_dir(self) -> None:
        self.db_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_from_json(self) -> None:
        if not self.db_file.exists():
            self.rules = []
            self.last_modified = 0.0
            return

        raw_text = self.db_file.read_text(encoding="utf-8").strip()
        if not raw_text:
            self.rules = []
            self.last_modified = self.db_file.stat().st_mtime
            return

        try:
            raw_data = json.loads(raw_text)
            if isinstance(raw_data, dict) and "rules" in raw_data:
                raw_data = raw_data["rules"]
            self.rules = MapRuleDatabase.model_validate(raw_data).root
            self.last_modified = self.db_file.stat().st_mtime
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Arquivo {self.db_file} corrompido.") from exc
        except ValidationError as exc:
            raise RuntimeError(
                f"Arquivo {self.db_file} nao segue o contrato MapRule."
            ) from exc

    def _check_reload(self) -> None:
        if self.db_file.exists() and self.db_file.stat().st_mtime > self.last_modified:
            self._load_from_json()

    def _save_to_json(self) -> None:
        self._ensure_data_dir()
        temporary_file = self.db_file.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(
                [rule.model_dump(mode="json") for rule in self.rules],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary_file.replace(self.db_file)
        self.last_modified = self.db_file.stat().st_mtime

    def list_rules(self, active_only: bool = False) -> list[MapRule]:
        self._check_reload()
        if active_only:
            return [rule for rule in self.rules if rule.active]
        return list(self.rules)

    def get_rule(self, rule_id: str) -> MapRule | None:
        self._check_reload()
        return next((rule for rule in self.rules if rule.id == rule_id), None)

    def create_rule(self, data: MapRule | dict[str, Any]) -> MapRule:
        rule = data if isinstance(data, MapRule) else MapRule.model_validate(data)
        rule = self._normalize_rule(rule)
        self.rules.append(rule)
        self._save_to_json()
        return rule

    def update_rule(self, rule_id: str, data: dict[str, Any]) -> MapRule | None:
        self._check_reload()
        for index, rule in enumerate(self.rules):
            if rule.id != rule_id:
                continue
            payload = rule.model_dump(mode="json")
            payload.update(data)
            payload["id"] = rule.id
            payload["created_at"] = rule.created_at
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated = self._normalize_rule(MapRule.model_validate(payload))
            self.rules[index] = updated
            self._save_to_json()
            return updated
        return None

    def delete_rule(self, rule_id: str) -> bool:
        self._check_reload()
        original_len = len(self.rules)
        self.rules = [rule for rule in self.rules if rule.id != rule_id]
        if len(self.rules) == original_len:
            return False
        self._save_to_json()
        return True

    def find_applicable_rule(
        self,
        product_like: Any,
        rules: Iterable[MapRule] | None = None,
    ) -> MapRule | None:
        rule_set = list(rules) if rules is not None else self.list_rules(active_only=True)
        return find_applicable_rule(product_like, rule_set)

    def _normalize_rule(self, rule: MapRule) -> MapRule:
        payload = rule.model_dump(mode="json")
        if rule.scope == "brand" and not payload.get("brand"):
            payload["brand"] = rule.target
        if rule.scope == "category" and not payload.get("category"):
            payload["category"] = rule.target
        if rule.scope == "product":
            if not payload.get("product_code") and not payload.get("product_url"):
                if "://" in rule.target or "/" in rule.target:
                    payload["product_url"] = rule.target
                else:
                    payload["product_code"] = rule.target
            if payload.get("product_url"):
                payload["normalized_url"] = normalize_url(payload["product_url"])
        return MapRule.model_validate(payload)


def _as_dict(product_like: Any) -> dict[str, Any]:
    if product_like is None:
        return {}
    if isinstance(product_like, dict):
        return dict(product_like)
    if hasattr(product_like, "model_dump"):
        return product_like.model_dump(mode="json")
    if hasattr(product_like, "dict"):
        return product_like.dict()
    return dict(vars(product_like))


def _rule_brand_matches(rule: MapRule, product: dict[str, Any]) -> bool:
    if not rule.brand:
        return True
    product_brand = product.get("brand") or product.get("brand_name") or product.get("marketplace")
    return normalize_text(rule.brand) == normalize_text(product_brand)


def _product_rule_matches(rule: MapRule, product: dict[str, Any]) -> bool:
    product_code = normalize_text(
        product.get("product_code")
        or product.get("sku")
        or product.get("target_sku")
    )
    rule_code = normalize_text(rule.product_code or rule.target)
    if product_code and rule_code and product_code == rule_code:
        return _rule_brand_matches(rule, product)

    product_url = normalize_url(product.get("url") or product.get("product_url"))
    rule_url = normalize_url(rule.product_url or rule.normalized_url or rule.target)
    return bool(product_url and rule_url and product_url == rule_url and _rule_brand_matches(rule, product))


def _category_rule_matches(rule: MapRule, product: dict[str, Any]) -> bool:
    product_category = normalize_text(product.get("category") or product.get("sub_category"))
    rule_category = normalize_text(rule.category or rule.target)
    return bool(product_category and product_category == rule_category and _rule_brand_matches(rule, product))


def _brand_rule_matches(rule: MapRule, product: dict[str, Any]) -> bool:
    product_brand = normalize_text(product.get("brand") or product.get("brand_name") or product.get("marketplace"))
    rule_brand = normalize_text(rule.brand or rule.target)
    return bool(product_brand and product_brand == rule_brand)


def find_applicable_rule(
    product_like: Any,
    rules: Iterable[MapRule],
) -> MapRule | None:
    product = _as_dict(product_like)
    active_rules = [rule for rule in rules if rule.active]
    matchers = (
        ("product", _product_rule_matches),
        ("category", _category_rule_matches),
        ("brand", _brand_rule_matches),
    )
    for scope, matcher in matchers:
        for rule in active_rules:
            if rule.scope == scope and matcher(rule, product):
                return rule
    return None


map_rules_service = MapRuleService()
