import json
import os
from typing import Dict, List, Optional
from models import DynamicBrand, DynamicBrandCreate, CategoryMapping

DB_FILE = "dynamic_brands.json"


class BrandManagerService:
    def __init__(self):
        self.brands: Dict[str, DynamicBrand] = {}
        self._load_db()

    def _load_db(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in data.items():
                    self.brands[key] = DynamicBrand(**val)

    def _save_db(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            data = {k: v.model_dump() for k, v in self.brands.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower()
        if key in self.brands:
            raise ValueError(f"A marca {key} já existe.")

        new_brand = DynamicBrand(**data.model_dump())
        self.brands[key] = new_brand
        self._save_db()
        return new_brand

    def list_brands(self) -> List[DynamicBrand]:
        return list(self.brands.values())

    def update_mappings(
        self, brand_key: str, mappings: List[CategoryMapping]
    ) -> DynamicBrand:
        key = brand_key.lower()
        if key not in self.brands:
            raise KeyError(f"Marca {key} não encontrada.")

        self.brands[key].mappings = mappings
        self._save_db()
        return self.brands[key]


brand_service = BrandManagerService()
