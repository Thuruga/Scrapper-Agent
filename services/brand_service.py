"""
BrandManagerService — persistência dual (Supabase ou JSON local).

- Se SUPABASE_URL + SUPABASE_KEY estiverem no ambiente → usa Supabase (produção).
- Caso contrário → usa data/brands.json (dev local, comportamento anterior).

Seed automático: na primeira inicialização com Supabase vazio, importa brands.json.
"""

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


class BrandDatabase(RootModel):
    root: Dict[str, DynamicBrand]


def _use_supabase() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


class BrandManagerService:
    def __init__(self):
        self.brands: Dict[str, DynamicBrand] = {}
        self.last_modified = 0
        self.updated_event = asyncio.Event()

        if not _use_supabase():
            self._ensure_db_dir()
            self._load_from_json()

    # ------------------------------------------------------------------
    # Infraestrutura local (JSON)
    # ------------------------------------------------------------------

    def _ensure_db_dir(self):
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)

    def _load_from_json(self):
        """Carrega e valida o arquivo JSON de marcas."""
        if os.path.exists(DB_FILE):
            try:
                self.last_modified = os.path.getmtime(DB_FILE)
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self.brands = {}
                        return
                    raw_data = json.loads(content)
                    validated_db = BrandDatabase.model_validate(raw_data)
                    self.brands = validated_db.root
                    logger.info(f"[OK] {len(self.brands)} marcas carregadas de {DB_FILE}")
            except json.JSONDecodeError as e:
                logger.error(f"[ERROR] JSON corrompido: {e}")
                raise RuntimeError(f"Arquivo {DB_FILE} corrompido.")
            except ValidationError as e:
                logger.error(f"[ERROR] Schema inválido: {e}")
                raise RuntimeError(f"Arquivo {DB_FILE} não segue o contrato DynamicBrand.")
            except Exception as e:
                logger.error(f"[ERROR] Erro inesperado ao carregar marcas: {e}")
                raise

    def _save_to_json(self):
        try:
            self._ensure_db_dir()
            with open(DB_FILE, "w", encoding="utf-8") as f:
                data = {k: v.model_dump() for k, v in self.brands.items()}
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.updated_event.set()
            self.updated_event.clear()
        except Exception as e:
            logger.error(f"[ERROR] Erro ao salvar brands.json: {e}")

    def _check_reload(self):
        """Recarrega se o JSON foi modificado externamente (dev local)."""
        if not _use_supabase() and os.path.exists(DB_FILE):
            mtime = os.path.getmtime(DB_FILE)
            if mtime > self.last_modified:
                logger.info("Mudança externa detectada, recarregando brands.json...")
                self._load_from_json()

    # ------------------------------------------------------------------
    # Infraestrutura Supabase
    # ------------------------------------------------------------------

    def _supabase_row_to_brand(self, row: dict) -> DynamicBrand:
        """Converte uma linha do Supabase para DynamicBrand."""
        mappings_raw = row.get("mappings") or []
        row["mappings"] = [CategoryMapping(**m) for m in mappings_raw]
        row.pop("created_at", None)
        return DynamicBrand.model_validate(row)

    def load_from_supabase(self):
        """
        Carrega marcas do Supabase de forma síncrona (chamado no startup).
        Executa seed automático se a tabela estiver vazia.
        """
        from db import get_supabase_client
        client = get_supabase_client()
        if not client:
            return

        try:
            result = client.table("brands").select("*").execute()
            rows = result.data or []

            if not rows:
                logger.info("[SEED] Tabela 'brands' vazia. Executando seed a partir de brands.json...")
                self._seed_supabase(client)
                result = client.table("brands").select("*").execute()
                rows = result.data or []

            self.brands = {}
            for row in rows:
                brand = self._supabase_row_to_brand(row)
                self.brands[brand.brand_key] = brand

            logger.info(f"[OK] {len(self.brands)} marcas carregadas do Supabase.")
        except Exception as e:
            logger.error(f"[ERROR] Falha ao carregar do Supabase: {e}. Usando in-memory vazio.")

    def _seed_supabase(self, client):
        """Importa brands.json para o Supabase (apenas na primeira inicialização)."""
        if not os.path.exists(DB_FILE):
            logger.warning("[SEED] brands.json não encontrado. Sem seed.")
            return
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = []
            for key, brand_data in data.items():
                row = {**brand_data}
                # Supabase espera JSONB para mappings
                row["mappings"] = row.get("mappings", [])
                row.pop("created_at", None)
                rows.append(row)
            if rows:
                client.table("brands").upsert(rows).execute()
                logger.info(f"[SEED] {len(rows)} marcas importadas para o Supabase.")
        except Exception as e:
            logger.error(f"[SEED] Falha no seed: {e}")

    def _upsert_to_supabase(self, brand: DynamicBrand):
        from db import get_supabase_client
        client = get_supabase_client()
        if not client:
            return
        try:
            row = brand.model_dump()
            row["mappings"] = [m.model_dump() for m in brand.mappings]
            client.table("brands").upsert(row).execute()
        except Exception as e:
            logger.error(f"[ERROR] Falha ao salvar no Supabase: {e}")

    def _delete_from_supabase(self, brand_key: str):
        from db import get_supabase_client
        client = get_supabase_client()
        if not client:
            return
        try:
            client.table("brands").delete().eq("brand_key", brand_key).execute()
        except Exception as e:
            logger.error(f"[ERROR] Falha ao deletar do Supabase: {e}")

    # ------------------------------------------------------------------
    # API Pública (agnóstica de backend)
    # ------------------------------------------------------------------

    def _save(self, brand: Optional[DynamicBrand] = None):
        """Persiste no backend ativo (Supabase ou JSON)."""
        if _use_supabase():
            if brand:
                self._upsert_to_supabase(brand)
        else:
            self._save_to_json()

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower().strip()
        if key in self.brands:
            self.brands[key].domain = data.domain
            self.brands[key].brand_name = data.brand_name
        else:
            new_brand = DynamicBrand(**data.model_dump())
            self.brands[key] = new_brand

        self._save(self.brands[key])
        return self.brands[key]

    def save_brand(self, brand_data: dict):
        key = brand_data.get("brand_key", "").lower().strip()
        if not key:
            return
        self.brands[key] = DynamicBrand.model_validate(brand_data)
        self._save(self.brands[key])

    def list_brands(self) -> List[DynamicBrand]:
        self._check_reload()
        return list(self.brands.values())

    def get_brand(self, brand_key: str) -> Optional[DynamicBrand]:
        self._check_reload()
        return self.brands.get(brand_key.lower())

    def update_mappings(self, brand_key: str, mappings: List[CategoryMapping]) -> DynamicBrand:
        key = brand_key.lower()
        if key not in self.brands:
            raise KeyError(f"Marca {key} não encontrada.")
        self.brands[key].mappings = mappings
        self._save(self.brands[key])
        return self.brands[key]

    def delete_brand(self, brand_key: str) -> bool:
        key = brand_key.lower().strip()
        if key in self.brands:
            del self.brands[key]
            if _use_supabase():
                self._delete_from_supabase(key)
            else:
                self._save_to_json()
            logger.info(f"[DELETE] Marca '{key}' excluída.")
            return True
        return False


# Singleton
brand_service = BrandManagerService()
