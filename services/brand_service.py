import json
import os
import asyncio
import logging
from typing import Dict, List, Optional
from pydantic import RootModel, ValidationError
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping
# from services.vtex_api_scraper import VtexApiClient  <-- Movido para dentro do método para evitar import circular

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
                    logger.info(f"✅ {len(self.brands)} marcas carregadas com sucesso de {DB_FILE}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro de sintaxe no JSON de marcas: {e}")
                raise RuntimeError(f"Arquivo {DB_FILE} corrompido: Erro de sintaxe JSON.")
            except ValidationError as e:
                logger.error(f"❌ Erro de validação no Schema de marcas: {e}")
                raise RuntimeError(f"Arquivo {DB_FILE} não segue o contrato DynamicBrand.")
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
            self.updated_event.clear() # Limpa para o próximo sinal
        except Exception as e:
            logger.error(f"❌ Erro ao salvar banco de marcas: {e}")

    def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
        key = data.brand_key.lower().strip()
        # Sanitize domain: remove https://, http:// and trailing /
        clean_domain = data.domain.replace("https://", "").replace("http://", "").strip("/")
        
        if key in self.brands:
            self.brands[key].domain = clean_domain
            self.brands[key].brand_name = data.brand_name
        else:
            data_dict = data.model_dump()
            data_dict["domain"] = clean_domain
            new_brand = DynamicBrand(**data_dict)
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
        Tenta mapear categorias automaticamente buscando a árvore VTEX 
        e comparando com as categorias canônicas, testando a validade de cada link.
        Adição TOTALMENTE automática de tudo que for válido.
        """
        from services.vtex_api_scraper import VtexApiClient
        from services.category_mapping import _RAW_CATEGORIES
        
        brand = self.brands.get(brand_key)
        if not brand:
            return

        # Limpeza do domínio (remove protocolos se houver)
        domain = brand.domain.replace("https://", "").replace("http://", "").strip("/")
        logger.info(f"🤖 Iniciando Onboarding TOTAL para {brand_key} ({domain})...")
        
        try:
            # 1. Buscar árvore real da VTEX (API + Extreme Fallback)
            vtex_tree = await VtexApiClient.fetch_categories(domain)
            if not vtex_tree:
                logger.warning(f"⚠️ Não foi possível obter categorias para {brand_key}")
                return

            # 2. Achatar e Limpar a Árvore para facilitar busca
            flat_vtex = []
            seen_paths = set()

            def flatten(nodes):
                if not isinstance(nodes, list):
                    return
                for node in nodes:
                    if not isinstance(node, dict):
                        continue
                    name = node.get("name", "").lower().strip()
                    url = node.get("url", "")
                    
                    if url:
                        path = url
                        if "http" in url:
                            parsed_path = "/".join(url.split("/")[3:])
                            path = "/" + parsed_path if parsed_path else "/"
                        if not path.startswith("/"): path = "/" + path
                    else:
                        path = f"/c/{node.get('id')}"

                    if path not in seen_paths:
                        flat_vtex.append({"name": name, "path": path})
                        seen_paths.add(path)

                    if node.get("children"):
                        flatten(node["children"])
            
            flatten(vtex_tree)

            # 3. Validação Massiva de Links (Semaphore para não travar a CPU/Rede)
            logger.info(f"🧪 Testando {len(flat_vtex)} links descobertos para {brand_key}...")
            semaphore = asyncio.Semaphore(10) # Até 10 validações simultâneas
            
            async def validate(item):
                async with semaphore:
                    full_url = f"https://{domain}{item['path']}"
                    is_valid = await VtexApiClient.validate_url(full_url)
                    return item if is_valid else None

            # Executa validações em paralelo
            tasks = [validate(item) for item in flat_vtex]
            results = await asyncio.gather(*tasks)
            valid_items = [r for r in results if r is not None]

            # 4. Mapeamento Inteligente e Persistência Incremental
            brand.mappings = [] # Limpa mappings anteriores para o novo onboarding
            
            for item in valid_items:
                # Tenta encontrar um correspondente canônico
                match_can = next(
                    (c for c in _RAW_CATEGORIES 
                     if c["label"].lower() == item["name"] or item["name"] in c["label"].lower()), 
                    None
                )
                
                slug = match_can["slug"] if match_can else item["name"].replace(" ", "-").lower()
                label = item["name"].capitalize()
                
                mapping = CategoryMapping(
                    canonical_slug=slug,
                    vtex_fq_path=item["path"],
                    label=label
                )
                
                # Adiciona e salva imediatamente para o frontend ver o progresso
                brand.mappings.append(mapping)
                self._save_db()
                logger.info(f"✅ Categoria '{label}' validada e adicionada.")

            if brand.mappings:
                logger.info(f"✨ Onboarding concluído: {len(brand.mappings)} categorias adicionadas para {brand_key}")
            else:
                logger.warning(f"⚠️ Nenhuma categoria válida encontrada após varredura total para {brand_key}")

        except Exception as e:
            logger.error(f"❌ Erro no onboarding total de {brand_key}: {e}", exc_info=True)

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
