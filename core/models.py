"""
Modelo canônico de dados — Camada Bronze.

Contrato único compartilhado por todos os scrapers e pelo orquestrador.
Qualquer campo específico de uma marca que não se aplique a outra fica Optional.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict


class RawProductBronze(BaseModel):
    """Dado bruto de um produto concorrente, sem transformações."""

    url: str
    brand: str
    raw_title: str
    raw_description: str
    price_full: float
    price_discount: Optional[float] = None
    stock_availability: Optional[bool] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    composition: Optional[str] = None
    specifications: Dict[str, str] = Field(default_factory=dict)
