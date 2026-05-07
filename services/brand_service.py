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
                        f"✅ {len(self.brands)} marcas carregadas com sucesso de {DB_FILE}"
                    )
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro de sintaxe no JSON de marcas: {e}")
                raise RuntimeError(
                    f"Arquivo {DB_FILE} corrompido: Erro de sintaxe JSON."
                )
            except ValidationError as e:
                logger.error(f"❌ Erro de validação no Schema de marcas: {e}")
                raise RuntimeError(
                    f"Arquivo {DB_FILE} não segue o contrato DynamicBrand."
                )
            except Exception as e:
                logger.error(f"❌ Erro inesperado ao carregar marcas: {e}")
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
            logger.error(f"❌ Erro ao salvar banco de marcas: {e}")

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower().strip()
        if key in self.brands:
            self.brands[key].domain = data.domain
            self.brands[key].brand_name = data.brand_name
        else:
            new_brand = DynamicBrand(**data.model_dump())
            self.brands[key] = new_brand

        self._save_db()

        # Trigger async auto-mapping in the background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.auto_map_brand(key))
        except RuntimeError:
            # Caso não haja um loop rodando (ex: scripts de migração)
            pass

        return self.brands[key]

    async def auto_map_brand(self, brand_key: str):
        """
        Mapeia categorias automaticamente buscando a árvore VTEX,
        testando se os links realmente funcionam (HTTP < 400) e
        comparando com as categorias canônicas.
        """
        from services.vtex_api_scraper import VtexApiClient
        import aiohttp

        brand = self.brands.get(brand_key)
        if not brand:
            return

        logger.info(
            f"🤖 Iniciando auto-mapeamento e validação de links para {brand_key} ({brand.domain})..."
        )

        try:
            # 1. Buscar árvore real da VTEX
            vtex_tree = await VtexApiClient.fetch_categories(brand.domain)
            if not vtex_tree:
                logger.warning(f"⚠️ Não foi possível obter árvore VTEX para {brand_key}")
                return

            # 2. Achatar a árvore para facilitar busca
            flat_vtex = []

            def flatten(nodes):
                for node in nodes:
                    name = node.get("name", "").lower()
                    url = node.get("url", "")

                    if url:
                        path = url
                        if "http" in url:
                            path = "/" + "/".join(url.split("/")[3:])
                        if not path.startswith("/"):
                            path = "/" + path
                    else:
                        path = f"/c/{node.get('id')}"

                    flat_vtex.append({"name": name, "path": path})
                    if node.get("children"):
                        flatten(node["children"])

            flatten(vtex_tree)

            # 3. Buscar categorias canônicas
            from services.category_mapping import _RAW_CATEGORIES

            new_mappings = []

            # 4. Iniciar sessão HTTP para testar os links na prática
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
                }

                for canonical in _RAW_CATEGORIES:
                    slug = canonical["slug"]
                    label = canonical["label"].lower()

                    # Procura match direto ou por contive (ex: "Camisas" contido em "Camisaria")
                    match = next(
                        (
                            c
                            for c in flat_vtex
                            if label in c["name"] or c["name"] in label
                        ),
                        None,
                    )

                    if match:
                        test_url = f"https://{brand.domain}{match['path']}"
                        logger.info(f"🔍 Testando link candidato: {test_url}")

                        try:
                            # Testa se a página existe e responde corretamente
                            async with session.get(
                                test_url, headers=headers, timeout=10
                            ) as resp:
                                if (
                                    resp.status < 400
                                ):  # Se for 200 OK ou redirect válido
                                    new_mappings.append(
                                        CategoryMapping(
                                            canonical_slug=slug,
                                            vtex_fq_path=match["path"],
                                            label=match["name"].capitalize(),
                                        )
                                    )
                                    logger.info(
                                        f"✅ Link Válido! Salvo: {slug} -> {match['path']}"
                                    )
                                else:
                                    logger.warning(
                                        f"⚠️ Link quebrado ignorado (Status {resp.status}): {test_url}"
                                    )
                        except Exception as e:
                            logger.error(f"❌ Erro ao aceder à URL {test_url}: {e}")

            if new_mappings:
                brand.mappings = new_mappings
                self._save_db()
                logger.info(
                    f"✨ {len(new_mappings)} categorias testadas, validadas e mapeadas com sucesso para {brand_key}"
                )
            else:
                logger.warning(
                    f"⚠️ Nenhuma categoria com link a funcionar foi encontrada para {brand_key}."
                )

        except Exception as e:
            logger.error(f"❌ Erro no auto-mapeamento de {brand_key}: {e}")

    def list_brands(self) -> List[DynamicBrand]:
        return list(self.brands.values())

    def get_brand(self, brand_key: str) -> Optional[DynamicBrand]:
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
            logger.info(f"🗑️ Marca '{key}' excluída com sucesso.")
            return True
        return False


# Instância singleton
brand_service = BrandManagerService()
