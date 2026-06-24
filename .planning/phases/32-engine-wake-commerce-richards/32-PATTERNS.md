# Phase 32: Engine Wake Commerce — Richards - Mapa de Padrões

**Mapeado:** 2026-06-24
**Arquivos analisados:** 6 (2 novos de spike, 1 novo engine, 1 novo test, 2 modificações)
**Análogos encontrados:** 6 / 6

---

## Classificação de Arquivos

| Arquivo Novo/Modificado | Role | Data Flow | Análogo Mais Próximo | Qualidade |
|-------------------------|------|-----------|----------------------|-----------|
| `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` | utility (spike script) | request-response | `.planning/spikes/001-brand-gate-impact/experiment.py` | exact |
| `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` | doc (spike report) | — | `.planning/spikes/CONVENTIONS.md` + spikes 003-006 | exact |
| `backend/services/engines/wake_engine.py` | service (engine) | request-response | `backend/services/engines/sfcc_engine.py` (estrutura) + `backend/services/engines/shopify_engine.py` (transporte HTTP) | exact (composto) |
| `backend/services/engines/factory.py` | config (wiring) | request-response | `backend/services/engines/factory.py` L48-50 (bloco `sfcc`) | exact |
| `backend/core/models.py` | model | — | `backend/core/models.py` L221-224 (campos opcionais `vtex_account`/`review_store_id`) | exact |
| `backend/tests/test_wake_engine.py` | test | request-response | `backend/tests/test_sfcc_engine.py` | exact |

---

## Atribuições de Padrões

---

### `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` (utility, request-response)

**Análogo:** `backend/../.planning/spikes/001-brand-gate-impact/experiment.py`

**Padrão de bootstrap / path fix** (linhas 27-29 do análogo):
```python
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
```
Adaptar para 4 níveis acima se necessário (007 fica em `.planning/spikes/007-.../`); confirmar que `ROOT` aponta para a raiz do repositório.

**Padrão de uso do SessionManager para HTTP** (espelha `shopify_engine.py` L26-27):
```python
# Reusar SessionManager.get_session() — aiohttp compartilhado, sem browser
from core.session_manager import SessionManager

session = await SessionManager.get_session()
async with session.get(storefront_url, allow_redirects=False) as resp:
    html = await resp.text()
```
`allow_redirects=False` é o padrão de segurança aplicado em `routes_brands.py:44` (T-25-01-SR).

**Padrão de saída dupla (stdout + REPORT.md):**
O spike deve imprimir resumo no stdout e escrever `REPORT.md` no mesmo diretório, seguindo o layout das seções abaixo (REPORT.md).

**Adaptação necessária:** O spike é assíncrono (usa `aiohttp`); usar `asyncio.run(main())` no `if __name__ == "__main__"`. Verificar empiricamente as premissas A1-A6 do RESEARCH.md.

---

### `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` (doc)

**Análogo:** `.planning/spikes/CONVENTIONS.md` + estrutura dos REPORT.md dos spikes 003-006.

**Formato canônico do REPORT.md** (da seção "Convenção de Spikes" do RESEARCH.md, verificada contra os spikes existentes):
```markdown
# Spike 007 — Wake GraphQL Token Confirmation

## Veredito
**GO** ← (ou **NO-GO**)

## Evidência
- Endpoint: https://storefront-api.fbits.net/graphql
- Header: TCS-Access-Token: tcs_loja_xxxx (extraído de: <URL da home>)
- Query: search(query: "camisa")
- Resposta (≥1 produto): [{ productName: "...", aliasComplete: "...", prices.price: 799.0 }]

## Campos confirmados
| Campo | Disponível | Valor exemplo |
|-------|-----------|---------------|
| productName | sim/não | ... |
| aliasComplete | sim/não | ... |
| prices.price | sim/não | ... |
| images.url | sim/não | ... |
| available | sim/não | ... |

## Formato do preço
- Numérico float em reais (não centavos): CONFIRMADO / NÃO CONFIRMADO

## Token auto-extraído
- Estratégia: regex `storefrontAccessToken` no inline script
- Token encontrado em: <URL>
- Prefixo observado: tcs_loja_...

## Alvo testado
- [ ] Richards (www.richards.com.br) — primário
- [ ] Shop2gether (www.shop2gether.com.br) — fallback
```

**Adaptação necessária:** Preencher com evidência empírica real. O arquivo é gerado (ou completado) pelo executor do spike.

---

### `backend/services/engines/wake_engine.py` (service, request-response)

**Análogo estrutural:** `backend/services/engines/sfcc_engine.py`
**Análogo de transporte HTTP:** `backend/services/engines/shopify_engine.py`

**Padrão de imports** (espelha `sfcc_engine.py` L26-41):
```python
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from core.models import BrandSearchResult, SearchProductResult
from core.session_manager import SessionManager
from services.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)
```
Diferença em relação ao SFCC: importa `SessionManager` (HTTP-API, sem browser) e `re` (regex do token). Não importa `BrowserManager`.

**Padrão de constantes de módulo** (espelha `sfcc_engine.py` L48-64):
```python
GRAPHQL_ENDPOINT = "https://storefront-api.fbits.net/graphql"
DEFAULT_MAX_RESULTS: int = 10

_TOKEN_RE = re.compile(
    r"""storefrontAccessToken\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)
```

**Padrão de `__init__` fino** (espelha `sfcc_engine.py` L84-85):
```python
class WakeEngine(BaseEngine):
    def __init__(self, brand_key: str) -> None:
        self.brand_key = brand_key
        self._token_cache: Optional[str] = None  # cache por instância (D-05 / Armadilha 5)
```
Cache como atributo de instância, nunca de classe — cada `get_engine(brand_key)` cria uma nova instância.

**Padrão de `get_engine_name`** (espelha `sfcc_engine.py` L91-93):
```python
def get_engine_name(self) -> str:
    return "Wake"
```

**Padrão de `search()` com resolução de brand e retorno `BrandSearchResult`** (espelha `sfcc_engine.py` L99-176, simplificado para HTTP-API):
```python
async def search(
    self,
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    sort: Optional[str] = None,
    only_in_stock: bool = False,
    zipcode: Optional[str] = None,
    include_shipping: bool = False,
) -> BrandSearchResult:
    from services.brand_service import brand_service  # lazy — avoid circular import

    brand = brand_service.get_brand(self.brand_key)
    brand_name: str = (
        getattr(brand, "brand_name", None)
        or (brand.get("brand_name", self.brand_key) if isinstance(brand, dict) else self.brand_key)
    )

    token = await self._resolve_token(brand)
    if not token:
        raise ValueError(
            f"Token Wake não resolvido para '{self.brand_key}'. "
            "Configure wake_access_token na marca ou verifique o storefront."
        )

    # POST GraphQL ...
    session = await SessionManager.get_session()
    # ... (ver Padrão 4 da RESEARCH.md para a query GraphQL)

    return BrandSearchResult(
        brand_key=self.brand_key,
        brand_name=brand_name,
        products=validated_products,
        total_found=len(validated_products),
    )
```
O `raise ValueError` no caminho de token ausente é capturado pelo `_search_one` de `factory.py:92-105` e vira `BrandSearchResult.error` (D-07 — nunca 0 produtos silenciosos).

**Padrão de Quality Gates após parse** (espelha `sfcc_engine.py` L220-239):
```python
# CAT-01: filtro de moda masculina
filtered = self.filter_mens_fashion(parsed_dicts)

# Quality Gate Pydantic — rejeita sem url/raw_title/price_full/image_url
validated: List[SearchProductResult] = []
for p in filtered:
    validated_dict = self.validate_single(p)
    if validated_dict:
        validated.append(
            SearchProductResult(
                brand=brand_name,
                product_name=validated_dict["raw_title"],
                url=validated_dict["url"],
                price_full=validated_dict.get("price_full"),
                image_url=validated_dict.get("image_url"),
                available=validated_dict.get("stock_availability"),
            )
        )
```

**Padrão de `calculate_shipping` → None** (espelha `sfcc_engine.py` L244-255 e `shopify_engine.py` L121-123):
```python
async def calculate_shipping(
    self, product: Any, zipcode: str
) -> Optional[Dict[str, Any]]:
    return None  # D-08: sem checkout público; evita badge "Frete Grátis" indevido
```

**Padrão de stubs de categoria** (espelha D-06/D-08; `sfcc_engine.py` retorna `[]` em exceção):
```python
async def discover_categories(self) -> List[Dict[str, Any]]:
    return []  # D-08: stub gracioso; implementação real deferida

async def get_catalog(self) -> List[Dict[str, Any]]:
    return []  # D-08: stub gracioso
```
Para `run_bulk_scrape` e `get_product_details`, stub com `return` / `return None` respectivamente.

**Padrão `_resolve_token` (novo, sem análogo direto — usar lógica de 3 etapas):**
```python
async def _resolve_token(self, brand=None) -> Optional[str]:
    # 1. Override manual (D-06) — campo wake_access_token da marca
    if brand:
        override = getattr(brand, "wake_access_token", None) or (
            brand.get("wake_access_token") if isinstance(brand, dict) else None
        )
        if override:
            return override

    # 2. Cache em memória por instância (D-05 / Armadilha 5)
    if self._token_cache:
        return self._token_cache

    # 3. Auto-extração via GET na home page da loja (D-05)
    # ... GET {domain}, bs4/regex _TOKEN_RE
    # self._token_cache = token_extraido
    # return self._token_cache

    # 4. None → caller levanta ValueError claro (D-07)
    return None
```

**Adaptação necessária:** Os campos exatos retornados pela GraphQL (especialmente `aliasComplete` e `images.url` dentro de `search.products.edges.node`) devem ser confirmados pelo spike antes de finalizar o parser. Ver Armadilhas 2-4 do RESEARCH.md.

---

### `backend/services/engines/factory.py` — MODIFICAÇÃO (L57-60)

**Análogo:** `backend/services/engines/factory.py` L48-50 (bloco `sfcc` já existente).

**Padrão atual a substituir** (`factory.py` L57-60, VERIFIED):
```python
if engine_type == "wake":
    raise NotImplementedError(
        f"Engine 'wake' para '{brand_key}' ainda não disponível (Phase 32 pendente)."
    )
```

**Padrão novo** (cópia exata do bloco `sfcc` L48-50, trocando nomes):
```python
if engine_type == "wake":
    from services.engines.wake_engine import WakeEngine  # noqa: PLC0415
    return WakeEngine(brand_key)
```
Import lazy dentro de `get_engine` — mesmo padrão do `SFCCEngine` — preserva segurança contra import circular.

**Adaptação necessária:** Substituição cirúrgica de 3 linhas. Nenhuma outra linha de `factory.py` é alterada. O bloco `if engine_type == "wake":` fica logo após o bloco `sfcc`.

---

### `backend/core/models.py` — MODIFICAÇÃO (L207-226)

**Análogo:** `backend/core/models.py` L221-224 — campos opcionais `vtex_account` e `review_store_id` em `DynamicBrandCreate`.

**Padrão existente** (`models.py` L221-224, VERIFIED):
```python
review_provider: Optional[str] = "none"  # ex: "trustvox", "vtex_native"
review_store_id: Optional[str] = None  # ex: "78800"
vtex_account: Optional[str] = None  # ex: "foxton" (se diferente do domínio)
engine: Optional[str] = "vtex"  # ex: "vtex", "shopify"
logo_url: Optional[str] = None  # ex: "https://.../logo.png"
```

**Linha a adicionar** (após `logo_url`, em `DynamicBrandCreate`):
```python
wake_access_token: Optional[str] = None  # override manual do token público de storefront Wake (D-06)
```
Campo também herdado por `DynamicBrand` (que é subclasse de `DynamicBrandCreate`) — nenhuma alteração adicional necessária no modelo filho.

**Adaptação necessária:** Adição de 1 linha em `DynamicBrandCreate`. Marcas existentes que não têm o campo continuam válidas (`Optional` com default `None`).

---

### `backend/tests/test_wake_engine.py` (test, request-response)

**Análogo:** `backend/tests/test_sfcc_engine.py`

**Padrão de import e mock seam** (`test_sfcc_engine.py` L19-29):
```python
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock seam para SessionManager (aiohttp — não browser)
_SESSION_GET_TARGET = "core.session_manager.SessionManager.get_session"
```
No Wake, o mock alvo é `SessionManager.get_session` (aiohttp), não `BrowserManager.fetch_html` (browser) como no SFCC.

**Padrão de fixture de resposta GraphQL** (análogo inline HTML do SFCC, adaptado para JSON):
```python
import json

_GRAPHQL_RESPONSE = {
    "data": {
        "search": {
            "products": {
                "edges": [
                    {
                        "node": {
                            "productName": "Camisa Slim Richards",
                            "aliasComplete": "produto/camisa-slim-123",
                            "prices": {"price": 799.0},
                            "images": [{"url": "https://www.richards.com.br/img/camisa.jpg"}],
                            "available": True,
                        }
                    }
                ]
            }
        }
    }
}
```

**Padrão de teste de factory** (`test_sfcc_engine.py` L218-233, adaptar para Wake):
```python
class TestWakeFactory:
    def test_factory_returns_wake_engine(self):
        """SC-3: EngineFactory.get_engine para marca wake retorna WakeEngine."""
        from services.engines.factory import EngineFactory
        from services.engines.wake_engine import WakeEngine

        mock_brand = MagicMock()
        mock_brand.engine = "wake"

        with patch(
            "services.engines.factory.brand_service.get_brand",
            return_value=mock_brand,
        ):
            engine = EngineFactory.get_engine("richards")
        assert isinstance(engine, WakeEngine)
```

**Padrão de teste de busca com session mockada** (espelha `test_sfcc_engine.py` L262-278):
```python
class TestWakeEngineSearch:
    def test_search_returns_products(self):
        """SC-2: search('camisa') retorna BrandSearchResult com ≥1 produto."""
        from services.engines.wake_engine import WakeEngine
        from core.models import BrandSearchResult

        mock_resp = AsyncMock()
        mock_resp.json = AsyncMock(return_value=_GRAPHQL_RESPONSE)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_resp)

        with patch(_SESSION_GET_TARGET, return_value=mock_session):
            with patch("services.brand_service.brand_service.get_brand",
                       return_value=MagicMock(brand_name="Richards",
                                              wake_access_token="tcs_loja_test",
                                              domain="www.richards.com.br")):
                engine = WakeEngine("richards")
                result = asyncio.run(engine.search("camisa", max_results=3))

        assert isinstance(result, BrandSearchResult)
        assert len(result.products) >= 1
```

**Padrão de teste de token ausente → erro claro** (SC-4 / D-07):
```python
class TestWakeTokenFailure:
    def test_missing_token_returns_error(self):
        """D-07: Token não resolvido → BrandSearchResult.error, nunca lista vazia silenciosa."""
        from services.engines.factory import EngineFactory
        from core.models import BrandSearchResult

        mock_brand = MagicMock()
        mock_brand.engine = "wake"
        mock_brand.wake_access_token = None  # sem override

        with patch("services.engines.factory.brand_service.get_brand", return_value=mock_brand):
            with patch("services.engines.wake_engine.SessionManager.get_session",
                       side_effect=Exception("network error")):
                result = asyncio.run(
                    EngineFactory().search_all_brands("camisa", brands=["richards"])
                )

        assert result[0].error is not None
        assert result[0].error != ""
```

**Remoção obrigatória:** `test_sfcc_engine.py` L235-249 (`test_factory_wake_still_raises`) deve ser **deletado ou substituído** por `test_factory_returns_wake_engine` acima — esse teste existe explicitamente como marcador de "Phase 32 pendente" e torna-se inválido após o wiring.

**Adaptação necessária:** O mock de `SessionManager.get_session` para aiohttp precisa simular o context manager `async with session.post(...) as resp:` — ver padrão acima. Confirmar no spike se o POST GraphQL usa `session.post(url, json={...})` diretamente ou via wrapper.

---

## Padrões Compartilhados

### Resolução de brand_key → domínio/nome
**Fonte:** `backend/services/engines/sfcc_engine.py` L121-145
**Aplicar a:** `wake_engine.py` (método `search`, método `_resolve_token`)
```python
from services.brand_service import brand_service  # lazy — avoid circular import

brand = brand_service.get_brand(self.brand_key)
domain: str = ""
brand_name: str = self.brand_key
if brand:
    domain = getattr(brand, "domain", None) or (
        brand.get("domain", "") if isinstance(brand, dict) else ""
    )
    brand_name = getattr(brand, "brand_name", None) or (
        brand.get("brand_name", self.brand_key) if isinstance(brand, dict) else self.brand_key
    )
if not domain:
    domain = f"{self.brand_key}.com.br"
```

### Import lazy dentro de `get_engine` (anti-circular)
**Fonte:** `backend/services/engines/factory.py` L48-50
**Aplicar a:** `factory.py` (bloco `wake` L57-60 substituído)
```python
if engine_type == "sfcc":
    from services.engines.sfcc_engine import SFCCEngine  # noqa: PLC0415
    return SFCCEngine(brand_key)
# → espelhar exatamente para wake:
if engine_type == "wake":
    from services.engines.wake_engine import WakeEngine  # noqa: PLC0415
    return WakeEngine(brand_key)
```

### Captura de erro por marca sem derrubar o gather
**Fonte:** `backend/services/engines/factory.py` L92-105
**Aplicar a:** Nenhuma modificação necessária — já captura qualquer `Exception` incluindo `ValueError` do token não resolvido
```python
async def _search_one(brand_key: str) -> BrandSearchResult:
    try:
        engine = self.get_engine(brand_key)
        return await engine.search(...)
    except Exception as e:
        return BrandSearchResult(brand_key=brand_key, brand_name=brand_key, error=str(e))
```

### Quality Gates (filter + validate)
**Fonte:** `backend/services/engines/sfcc_engine.py` L220-239
**Aplicar a:** `wake_engine.py` (dentro de `search()`, após parse dos nós GraphQL)
Ordem obrigatória: (1) `self.filter_mens_fashion(parsed_dicts)` → (2) `self.validate_single(p)` → (3) construir `SearchProductResult`.

### Bootstrap do spike (path fix)
**Fonte:** `.planning/spikes/001-brand-gate-impact/experiment.py` L27-29
**Aplicar a:** `.planning/spikes/007-.../experiment.py`
```python
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
```

---

## Sem Análogo Encontrado

| Arquivo | Role | Data Flow | Motivo |
|---------|------|-----------|--------|
| `wake_engine._resolve_token()` (método interno) | utility | request-response | Nenhum engine existente faz auto-extração de token via GET HTML + regex. O padrão mais próximo é a detecção de engine por HTML em `routes_brands.py:44`, mas a semântica é diferente. Usar a lógica de 3 etapas descrita em RESEARCH.md Padrão 5 + Armadilha 1. |
| Query GraphQL Wake (body do POST) | — | — | Nenhuma query GraphQL existe no projeto; o padrão de corpo JSON é padrão aiohttp. Usar a query `WakeSearch` do RESEARCH.md Padrão 4, **confirmando campos no spike** (A2, A3 ASSUMED). |

---

## Metadata

**Escopo de busca de análogos:** `backend/services/engines/`, `backend/core/`, `backend/tests/`, `.planning/spikes/`
**Arquivos lidos:** `sfcc_engine.py`, `shopify_engine.py`, `factory.py`, `models.py` (L200-257), `test_sfcc_engine.py`, `spikes/001.../experiment.py`
**Data do mapeamento:** 2026-06-24

### Arquivos read_first obrigatórios por tarefa

| Tarefa | Arquivos a ler antes de implementar |
|--------|-------------------------------------|
| Spike Wave 0 (`experiment.py`) | `.planning/spikes/001-brand-gate-impact/experiment.py`, `.planning/spikes/CONVENTIONS.md`, `backend/core/session_manager.py` |
| `wake_engine.py` | `backend/services/engines/sfcc_engine.py`, `backend/services/engines/shopify_engine.py`, `backend/services/engines/base_engine.py`, `backend/core/session_manager.py` |
| `factory.py` (L57-60) | `backend/services/engines/factory.py` (todo) |
| `models.py` (campo `wake_access_token`) | `backend/core/models.py` L207-226 |
| `test_wake_engine.py` | `backend/tests/test_sfcc_engine.py`, `backend/tests/test_engine_detection.py` |
