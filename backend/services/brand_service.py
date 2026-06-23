"""Cadastro de marcas persistido exclusivamente em JSON local."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import RootModel, ValidationError

from core.models import CategoryMapping, DynamicBrand, DynamicBrandCreate

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_FILE = DATA_DIR / "brands.json"

logger = logging.getLogger("BrandService")


class BrandDatabase(RootModel):
    root: Dict[str, DynamicBrand]


class BrandManagerService:
    def __init__(self):
        self.brands: Dict[str, DynamicBrand] = {}
        self.last_modified = 0.0
        self.updated_event = asyncio.Event()
        self._ensure_data_dir()
        self._load_from_json()

    @staticmethod
    def _ensure_data_dir() -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _load_from_json(self) -> None:
        """Carrega e valida o cadastro local de marcas."""
        if not DB_FILE.exists():
            logger.warning("Cadastro de marcas nao encontrado em %s", DB_FILE)
            return

        try:
            raw_data = json.loads(DB_FILE.read_text(encoding="utf-8"))
            validated_db = BrandDatabase.model_validate(raw_data)
            self.brands = validated_db.root
            self.last_modified = DB_FILE.stat().st_mtime
            logger.info("%d marcas carregadas de %s", len(self.brands), DB_FILE)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Arquivo {DB_FILE} corrompido.") from exc
        except ValidationError as exc:
            raise RuntimeError(
                f"Arquivo {DB_FILE} nao segue o contrato DynamicBrand."
            ) from exc

    def _save_to_json(self) -> None:
        """Salva o cadastro de forma atomica para evitar arquivo parcial."""
        self._ensure_data_dir()
        data = {key: brand.model_dump() for key, brand in self.brands.items()}
        temporary_file = DB_FILE.with_suffix(".json.tmp")
        temporary_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary_file.replace(DB_FILE)
        self.last_modified = DB_FILE.stat().st_mtime
        self.updated_event.set()
        self.updated_event.clear()

    def _check_reload(self) -> None:
        if DB_FILE.exists() and DB_FILE.stat().st_mtime > self.last_modified:
            logger.info("Mudanca externa detectada; recarregando marcas.")
            self._load_from_json()

    def _save(self, brand: Optional[DynamicBrand] = None) -> None:
        """Ponto unico de persistencia, mantido simples para testes e extensoes."""
        self._save_to_json()

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower().strip()
        if key in self.brands:
            self.brands[key].domain = data.domain
            self.brands[key].brand_name = data.brand_name
        else:
            self.brands[key] = DynamicBrand(**data.model_dump())

        self._save(self.brands[key])
        return self.brands[key]

    def save_brand(self, brand_data: dict) -> None:
        key = brand_data.get("brand_key", "").lower().strip()
        if not key:
            return
        self.brands[key] = DynamicBrand.model_validate(brand_data)
        self._save(self.brands[key])

    def list_brands(self, active_only: bool = False) -> List[DynamicBrand]:
        self._check_reload()
        brands = list(self.brands.values())
        return [brand for brand in brands if brand.is_active] if active_only else brands

    def get_brand(self, brand_key: str) -> Optional[DynamicBrand]:
        self._check_reload()
        return self.brands.get(brand_key.lower())

    def set_active(self, brand_key: str, is_active: bool) -> Optional[DynamicBrand]:
        key = brand_key.lower()
        if key not in self.brands:
            return None
        self.brands[key].is_active = is_active
        self._save(self.brands[key])
        return self.brands[key]

    def update_mappings(
        self, brand_key: str, mappings: List[CategoryMapping]
    ) -> DynamicBrand:
        key = brand_key.lower()
        if key not in self.brands:
            raise KeyError(f"Marca {key} nao encontrada.")
        self.brands[key].mappings = mappings
        self._save(self.brands[key])
        return self.brands[key]

    def delete_brand(self, brand_key: str) -> bool:
        key = brand_key.lower().strip()
        if key not in self.brands:
            return False
        del self.brands[key]
        self._save()
        logger.info("Marca '%s' excluida.", key)
        return True


brand_service = BrandManagerService()
