from pydantic import BaseModel, Field
from typing import List, Optional


class CategoryMapping(BaseModel):
    canonical_slug: str  # ex: "polos", "camisas"
    vtex_fq_path: str  # ex: "C:/1/2/"
    label: str  # ex: "Polos Masculinas" (para o frontend exibir)


class DynamicBrandCreate(BaseModel):
    brand_key: str  # ex: "reserva", "aramis", "loja_nova"
    brand_name: str  # ex: "Reserva"
    domain: str  # ex: "www.usereserva.com"


class DynamicBrand(DynamicBrandCreate):
    mappings: List[CategoryMapping] = Field(default_factory=list)
    is_active: bool = True
