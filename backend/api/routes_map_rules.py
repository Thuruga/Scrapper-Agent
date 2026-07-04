"""Protected CRUD routes for MAP pricing rules."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from core.models import MapRule
from services.map_rules_service import map_rules_service


router = APIRouter(prefix="/map-rules", tags=["MAP Rules"])


class MapRuleCreateRequest(BaseModel):
    scope: Literal["product", "category", "brand"]
    target: str = Field(min_length=1)
    min_price: float = Field(gt=0)
    active: bool = True
    brand: str | None = None
    category: str | None = None
    product_code: str | None = None
    product_url: str | None = None
    notes: str | None = None


class MapRuleUpdateRequest(BaseModel):
    scope: Literal["product", "category", "brand"] | None = None
    target: str | None = Field(default=None, min_length=1)
    min_price: float | None = Field(default=None, gt=0)
    active: bool | None = None
    brand: str | None = None
    category: str | None = None
    product_code: str | None = None
    product_url: str | None = None
    notes: str | None = None


@router.get("", response_model=list[MapRule])
async def list_map_rules() -> list[MapRule]:
    return map_rules_service.list_rules()


@router.post("", response_model=MapRule, status_code=201)
async def create_map_rule(payload: MapRuleCreateRequest) -> MapRule:
    try:
        return map_rules_service.create_rule(payload.model_dump(exclude_unset=True))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{rule_id}", response_model=MapRule)
async def update_map_rule(rule_id: str, payload: MapRuleUpdateRequest) -> MapRule:
    updated = map_rules_service.update_rule(
        rule_id,
        payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Regra MAP nao encontrada")
    return updated


@router.delete("/{rule_id}", status_code=204)
async def delete_map_rule(rule_id: str) -> Response:
    if not map_rules_service.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Regra MAP nao encontrada")
    return Response(status_code=204)
