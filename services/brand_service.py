import json
import os
import asyncio
import logging
from typing import Dict, List, Optional
from pydantic import RootModel, ValidationError
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping

DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "brands.json")

logger = logging.getLogger("BrandService")


# Modelo para validação total do banco (Dicionário de marcas)
class BrandDatabase(RootModel):
    root: Dict[str, DynamicBrand]


class BrandManagerService:
    def __init__(self):
        self.brands: Dict[str, DynamicBrand] = {}
        self.last_modified = 0
        self._ensure_db_dir()
        self._load_db()
        # Evento para notificar outros serviços (como o orquestrador) sobre mudanças
        self.updated_event = asyncio.Event()

    def _ensure_db_dir(self):
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)

    def _load_db(self):
        """Carrega e valida rigorosamente o arquivo JSON de marcas."""
        if os.path.exists(DB_FILE):
            try:
                self.last_modified = os.path.getmtime(DB_FILE)
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self.brands = {}
                        return

                    raw_data = json.loads(content)
                    # Validação rigorosa com Pydantic
                    validated_db = BrandDatabase.model_validate(raw_data)
                    self.brands = validated_db.root
                    logger.info(
                        f"[OK] {len(self.brands)} marcas carregadas com sucesso de {DB_FILE}"
                    )
            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] Erro de sintaxe no JSON de marcas: {e}")
                raise RuntimeError(
                    f"Arquivo {DB_FILE} corrompido: Erro de sintaxe JSON."
                )
            except ValidationError as e:
                logger.error(f"[ERROR] Erro de validação no Schema de marcas: {e}")
                raise RuntimeError(
                    f"Arquivo {DB_FILE} não segue o contrato DynamicBrand."
                )
            except Exception as e:
                logger.error(f"[ERROR] Erro inesperado ao carregar marcas: {e}")
                raise

    def _save_db(self):
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                data = {k: v.model_dump() for k, v in self.brands.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
            # Sinaliza que houve mudança
            self.updated_event.set()
            self.updated_event.clear()  # Limpa para o próximo sinal
        except Exception as e:
            logger.error(f"[ERROR] Erro ao salvar banco de marcas: {e}")

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower().strip()
        if key in self.brands:
            self.brands[key].domain = data.domain
            self.brands[key].brand_name = data.brand_name
        else:
            new_brand = DynamicBrand(**data.model_dump())
            self.brands[key] = new_brand

        self._save_db()

        # Auto-mapping background trigger removed

        return self.brands[key]



    def save_brand(self, brand_data: dict):
        """Salva ou atualiza uma marca no banco."""
        key = brand_data.get("brand_key", "").lower().strip()
        if not key:
            return
        self.brands[key] = DynamicBrand.model_validate(brand_data)
        self._save_db()

    def _check_reload(self):
        """Verifica se o arquivo foi modificado externamente e recarrega se necessário."""
        if os.path.exists(DB_FILE):
            mtime = os.path.getmtime(DB_FILE)
            if mtime > self.last_modified:
                logger.info(f"Detectada mudança externa em {DB_FILE}, recarregando banco de marcas...")
                self._load_db()

    def list_brands(self) -> List[DynamicBrand]:
        self._check_reload()
        return list(self.brands.values())

    def get_brand(self, brand_key: str) -> Optional[DynamicBrand]:
        self._check_reload()
        return self.brands.get(brand_key.lower())

    def update_mappings(
        self, brand_key: str, mappings: List[CategoryMapping]
    ) -> DynamicBrand:
        key = brand_key.lower()
        if key not in self.brands:
            raise KeyError(f"Marca {key} não encontrada.")

        self.brands[key].mappings = mappings
        self._save_db()
        return self.brands[key]


    def delete_brand(self, brand_key: str) -> bool:
        """Exclui uma marca do banco de dados."""
        key = brand_key.lower().strip()
        if key in self.brands:
            del self.brands[key]
            self._save_db()
            logger.info(f"[DELETE] Marca '{key}' excluída com sucesso.")
            return True
        return False


# Instância singleton
brand_service = BrandManagerService()
