import logging
import difflib
from typing import List, Dict, Any, Optional
from services.vtex_api_scraper import VtexApiClient
from services.category_mapping import _CATEGORY_INDEX, CanonicalCategory
from services.brand_service import brand_service

logger = logging.getLogger("CategoryIntelligence")

class CategoryIntelligenceService:
    """
    Serviço de inteligência para descoberta e mapeamento automático de categorias.
    """

    @staticmethod
    async def discover_and_map(brand_key: str) -> List[Dict[str, Any]]:
        """
        Descobre as categorias reais da marca e tenta mapeá-las para as canônicas.
        """
        brand_data = brand_service.get_brand(brand_key)
        if not brand_data:
            logger.error(f"Marca {brand_key} não encontrada para descoberta.")
            return []

        # 1. Fetch categories from VTEX
        vtex_categories = await VtexApiClient.fetch_categories(brand_data.domain)
        if not vtex_categories:
            logger.warning(f"Nenhuma categoria encontrada para {brand_key}")
            return []

        # 2. Flatten and sanitize VTEX categories
        flat_categories = CategoryIntelligenceService._flatten_vtex_tree(vtex_categories)
        
        # 3. Perform matching
        suggestions = []
        canonical_list = list(_CATEGORY_INDEX.values())

        for v_cat in flat_categories:
            v_name = v_cat["name"].lower()
            v_path = v_cat["url"]
            
            # Tenta achar o melhor match canônico
            best_match: Optional[CanonicalCategory] = None
            highest_score = 0.0
            
            for c_cat in canonical_list:
                # Compara o nome da categoria VTEX com o label canônico
                score = difflib.SequenceMatcher(None, v_name, c_cat.label.lower()).ratio()
                
                # Se for um match exato ou muito próximo
                if score > highest_score and score > 0.6:
                    highest_score = score
                    best_match = c_cat
            
            if best_match:
                suggestions.append({
                    "vtex_name": v_cat["name"],
                    "vtex_path": v_path,
                    "canonical_slug": best_match.slug,
                    "canonical_label": best_match.label,
                    "confidence": round(highest_score, 2)
                })

        return suggestions

    @staticmethod
    async def run_background_discovery(brand_key: str):
        """
        Executa a descoberta e salva automaticamente os mapeamentos encontrados.
        """
        logger.info(f"[{brand_key}] Iniciando descoberta autônoma em background...")
        suggestions = await CategoryIntelligenceService.discover_and_map(brand_key)
        
        if not suggestions:
            logger.info(f"[{brand_key}] Nenhuma sugestão encontrada para mapeamento automático.")
            return

        brand_data = brand_service.get_brand(brand_key)
        if not brand_data:
            return

        # Filtra apenas mapeamentos com alta confiança (> 0.8) para automação total
        from core.models import CategoryMapping
        
        count = 0
        for s in suggestions:
            if s["confidence"] >= 0.8:
                # Verifica se já existe um mapeamento para esse slug
                exists = any(m.canonical_slug == s["canonical_slug"] for m in brand_data.mappings)
                if not exists:
                    mapping = CategoryMapping(
                        canonical_slug=s["canonical_slug"],
                        vtex_fq_path=s["vtex_path"],
                        label=s["canonical_label"]
                    )
                    brand_data.mappings.append(mapping)
                    count += 1
        
        if count > 0:
            brand_service.save_brand(brand_data.model_dump())
            logger.info(f"[{brand_key}] Automação concluída: {count} categorias mapeadas com sucesso.")
        else:
            logger.info(f"[{brand_key}] Nenhuma nova categoria com alta confiança para mapear.")

    @staticmethod
    def _flatten_vtex_tree(tree: List[Dict[str, Any]], parent_path: str = "") -> List[Dict[str, Any]]:

        """Achata a árvore de categorias da VTEX para uma lista simples de paths."""
        flat = []
        for node in tree:
            name = node.get("name", "")
            url = node.get("url", "")
            
            if name and url:
                flat.append({"name": name, "url": url})
            
            children = node.get("children", [])
            if children:
                flat.extend(CategoryIntelligenceService._flatten_vtex_tree(children, url))
        
        return flat

category_intelligence = CategoryIntelligenceService()
