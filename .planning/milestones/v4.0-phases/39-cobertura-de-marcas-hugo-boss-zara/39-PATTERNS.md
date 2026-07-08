# Phase 39: Cobertura de Marcas — Hugo Boss & Zara - Pattern Map

**Mapeado:** 2026-06-26
**Arquivos analisados:** 7 (novos/modificados)
**Analogs encontrados:** 7 / 7

---

## File Classification

| Novo/Modificado | Role | Data Flow | Analog mais próximo | Qualidade do match |
|-----------------|------|-----------|--------------------|--------------------|
| `backend/scripts/onboard_hugoboss_categories.py` (ou extensão de `onboard_vtex_brands.py`) | script / utility | batch | `backend/scripts/onboard_vtex_brands.py` | exact |
| `backend/data/brands.json` (patch: hugoboss.mappings) | config / data | CRUD | `backend/data/brands.json` (estado atual das demais marcas VTEX dinâmicas) | exact |
| `backend/tests/test_hugoboss_category_mapping.py` | test | request-response | `backend/tests/test_vtex_brand_onboarding_contract.py` | exact |
| `backend/tests/test_hugoboss_vtex_scan.py` | test | request-response | `backend/tests/test_vtex_brand_onboarding_contract.py` | exact |
| `.planning/spikes/010-zara-product-price/experiment.py` | spike / utility | event-driven (browser) | `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` | exact |
| `backend/services/engines/inditex_engine.py` (só em GO) | service / engine | request-response | `backend/services/engines/wake_engine.py` | role-match |
| `backend/services/engines/factory.py` (acrescentar branch inditex) | service / factory | request-response | `backend/services/engines/factory.py` (branches sfcc/wake existentes) | exact |

---

## Pattern Assignments

### `backend/scripts/onboard_hugoboss_categories.py` (script, batch)

**Analog:** `backend/scripts/onboard_vtex_brands.py`

**Imports pattern** (linhas 15–29 do analog):
```python
import asyncio
import sys
import os
from urllib.parse import urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.brand_service import brand_service
from services.engines.vtex_engine import VTEXEngine
from core.models import CategoryMapping
from scripts.onboard_vtex_brands import auto_match, persist_mappings
```

**Core pattern — discover_and_match** (linhas 313–330 do analog):
```python
async def discover_and_match(svc, brand_key: str) -> "tuple[int, list]":
    engine = VTEXEngine(brand_key)
    raw = await engine.discover_categories()
    for item in raw:
        # Pitfall 3 DEFUSED: item["path"] é URL completa; extrai path relativo
        item["rel_path"] = urlparse(item.get("path") or "").path
    return len(raw), auto_match(raw)
```

**Persistência pattern** (linhas 359–378 do analog):
```python
def persist_mappings(svc, brand_key: str, proposals: list) -> None:
    valid_proposals = [
        (slug, rel_path, label)
        for slug, rel_path, label in proposals
        if rel_path.startswith("/")
    ]
    mappings = [
        CategoryMapping(canonical_slug=slug, vtex_fq_path=rel_path, label=label)
        for slug, rel_path, label in valid_proposals
    ]
    svc.update_mappings(brand_key, mappings)
```

**Human-review gate** (linhas 337–352 do analog):
```python
def print_and_confirm(brand_key: str, proposals: list) -> bool:
    for slug, path, label in proposals:
        print(f"  {slug:12s} <- {label!r}  ({path})")
    matched_slugs = {slug for slug, _, _ in proposals}
    unmatched = sorted(CANONICAL_KEYWORDS.keys() - matched_slugs)
    if unmatched:
        print(f"  [SEM MATCH] slugs sem categoria encontrada: {unmatched}")
    print("Confirmar? [s/N] ", end="", flush=True)
    return input().strip().lower() == "s"
```

**Ponto crítico obrigatório:** O domínio da Hugo Boss deve ser passado como `"www.hugoboss.com.br"` (com `www.`). O analog usa `BRAND_TABLE` com domínios verbatim; o script da Hugo Boss deve fazer o mesmo. Ver `backend/data/brands.json` linha 461 para confirmar o domínio correto.

---

### `backend/data/brands.json` — patch hugoboss.mappings

**Analog:** estado persistido das demais marcas VTEX dinâmicas no mesmo arquivo

**Estrutura alvo após script:**
```json
"hugoboss": {
    "brand_key": "hugoboss",
    "brand_name": "Hugo Boss",
    "domain": "www.hugoboss.com.br",
    "engine": "vtex",
    "is_active": true,
    "mappings": [
        {"canonical_slug": "camisas",   "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "polos",     "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "camisetas", "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "calcas",    "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "bermudas",  "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "jaquetas",  "vtex_fq_path": "/...",  "label": "..."},
        {"canonical_slug": "infantil",  "vtex_fq_path": "/...",  "label": "..."}
    ]
}
```
Os paths reais são descobertos pelo script via `VtexApiClient`. Os slugs canônicos devem ser apenas os que `auto_match` confirmar como presentes no catálogo.

**Invariante a preservar:** todo `vtex_fq_path` começa com `"/"`. Teste de regressão `test_vtex_fq_path_is_relative` em `test_vtex_brand_onboarding_contract.py` detecta violação.

---

### `backend/tests/test_hugoboss_category_mapping.py` (test, request-response)

**Analog:** `backend/tests/test_vtex_brand_onboarding_contract.py`

**Imports + factory pattern** (linhas 1–64 do analog):
```python
import asyncio
import unittest.mock

import services.category_mapping as category_mapping_module
from services.brand_service import BrandManagerService
from services.category_mapping import _RAW_CATEGORIES, resolve_category_for_brands
from core.models import CategoryMapping, DynamicBrand
from scripts.onboard_vtex_brands import auto_match

VALID_SLUGS = {c["slug"] for c in _RAW_CATEGORIES}

def _make_service_with_vtex_brand(
    brand_key: str = "hugoboss",  # trocar default para hugoboss
    engine: str = "vtex",
    is_active: bool = True,
    mappings=None,
) -> BrandManagerService:
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    svc._check_reload = unittest.mock.MagicMock()
    svc.brands[brand_key] = DynamicBrand(
        brand_key=brand_key,
        brand_name="Hugo Boss",
        domain="www.hugoboss.com.br",
        engine=engine,
        is_active=is_active,
        mappings=mappings or [],
    )
    return svc
```

**Test: resolve retorna URL válida com mappings dinâmicos** (linhas 185–207 do analog, adaptado):
```python
def test_resolve_category_returns_valid_url_hugoboss(self):
    mappings = [
        CategoryMapping(
            canonical_slug="camisas",
            vtex_fq_path="/masculino/roupas/camisas",
            label="Camisas",
        ),
    ]
    svc = _make_service_with_vtex_brand(mappings=mappings)
    with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
        result = resolve_category_for_brands("camisas", ["hugoboss"])
    assert "hugoboss" in result
    url = result["hugoboss"]["url"]
    assert url.startswith("https://www.hugoboss.com.br/")
    assert url.endswith("/masculino/roupas/camisas")
```

**Test: get_canonical_categories inclui hugoboss** — adicionar `get_canonical_categories` ao imports e mockar `brand_service` com o svc em memória:
```python
from services.category_mapping import get_canonical_categories

def test_get_canonical_categories_includes_hugoboss(self):
    # ... svc com mappings populados ...
    with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
        result = get_canonical_categories()
    all_brands = [b for group in result for cat in group["categories"] for b in cat["available_brands"]]
    assert "hugoboss" in all_brands
```

---

### `backend/tests/test_hugoboss_vtex_scan.py` (test, request-response)

**Analog:** `backend/tests/test_vtex_brand_onboarding_contract.py`

**Core pattern — mock de VtexApiClient para scan offline:**
```python
import unittest.mock
from core.models import SearchProductResult, BrandSearchResult

def test_vtex_scan_returns_valid_schema(self):
    """VTEXEngine.search retorna SearchProductResult com schema valido (mock)."""
    mock_products = [
        SearchProductResult(
            brand="hugoboss",
            product_name="Camisa Social Hugo Boss",
            url="https://www.hugoboss.com.br/masculino/roupas/camisas/produto-teste",
            price_full=599.0,
        )
    ]
    with unittest.mock.patch(
        "services.engines.vtex_engine.VtexApiClient.search_products",
        return_value=mock_products,
    ):
        engine = VTEXEngine("hugoboss")
        result = asyncio.run(engine.search("camisa", max_results=3))
    assert isinstance(result, BrandSearchResult)
    assert len(result.products) >= 1
    for p in result.products:
        assert p.brand == "hugoboss"
        assert p.url.startswith("https://www.hugoboss.com.br/")
        assert p.price_full > 0
```

---

### `.planning/spikes/010-zara-product-price/experiment.py` (spike, event-driven browser)

**Analog:** `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py`

**Imports e configuração do browser** (linhas 1–49 do analog):
```python
from __future__ import annotations
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

SPIKE_DIR = Path(__file__).resolve().parent
REPORT_PATH = SPIKE_DIR / "REPORT.md"

CHROMIUM_ARGS = [
    "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
    "--disable-gpu", "--disable-extensions", "--disable-background-networking",
    "--disable-default-apps", "--disable-sync", "--mute-audio", "--no-first-run",
]
STEALTH_ARGS = CHROMIUM_ARGS + ["--disable-blink-features=AutomationControlled"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}
```

**Context pattern — pt-BR, viewport, locale, timezone** (linhas 69–77 do analog):
```python
def _new_context(browser: Any) -> Any:
    return browser.new_context(
        user_agent=USER_AGENT,
        java_script_enabled=True,
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        extra_http_headers=HEADERS,
    )
```

**Stealth apply pattern** (linhas 144–160 do analog):
```python
browser = playwright.chromium.launch(headless=True, args=STEALTH_ARGS)
context = _new_context(browser)
page = context.new_page()
Stealth().apply_stealth_sync(context)
response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
time.sleep(2.5)  # aguarda JS carregar conteúdo dinâmico
html = page.content()
```

**ProbeResult dataclass** (linhas 52–66 do analog — adaptar para Zara):
```python
@dataclass
class ProbeResult:
    label: str
    url: str
    mode: str
    ok: bool = False
    status: Optional[int] = None
    final_url: str = ""
    title: str = ""
    html_bytes: int = 0
    blocked_signals: list[str] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""
```

**choose_verdict pattern — gate GO/NO-GO** (linhas 252–257 do analog, adaptar critério D-05):
```python
def choose_verdict(first_round: list[dict], second_round: list[dict]) -> str:
    # D-05: GO = >=3 produtos reais, com reexecucao bem-sucedida
    if len(first_round) >= 3 and len(second_round) >= 3:
        return "GO"
    if first_round or second_round:
        return "GO_TECHNICAL"  # >=1 mas <3 sem repetição estável
    return "NO-GO"
```

**write_report pattern** (linhas 284–357 do analog — estrutura com veredito GO/NO-GO explícito + evidência reprodutível):
```python
def write_report(
    first_round: list[dict],
    second_round: list[dict],
    zara_probes: list[ProbeResult],
    verdict: str,
    exception: str = "",
) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    # ... corpo do REPORT.md com veredito explícito, tabelas de probes e produtos
    REPORT_PATH.write_text(report, encoding="utf-8")
```

**Main com try/except/finally sempre grava REPORT** (linhas 360–406 do analog):
```python
def main() -> int:
    verdict = "NO-GO"
    exception = ""
    try:
        with sync_playwright() as playwright:
            # probes + rounds aqui
            verdict = choose_verdict(first_round, second_round)
    except Exception as exc:  # noqa: BLE001 - always write report
        exception = f"{type(exc).__name__}: {exc}"
    finally:
        write_report(..., verdict, exception)
    print(json.dumps({"verdict": verdict, "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

**URL base para spike 010** (baseado no spike 008 linha 241 + D-07):
```python
# Spike 008 provou: zara.com/br + stealth → 200 + jsonld_product_marker
# spike 010: busca masculina (section=MAN), queries camiseta/calça (D-07)
ZARA_SEARCH_URL = "https://www.zara.com/br/pt/search?searchTerm={query}&section=MAN"
```

---

### `backend/services/engines/inditex_engine.py` (engine, request-response) — APENAS em GO

**Analog:** `backend/services/engines/wake_engine.py`

**Imports e estrutura base** (linhas 44–56 do analog):
```python
from __future__ import annotations
import logging
from typing import Any, List, Optional

from core.models import BrandSearchResult, SearchProductResult
from services.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)
```

**Padrão de construtor e get_engine_name** (padrão WakeEngine):
```python
class InditexEngine(BaseEngine):
    def __init__(self, brand_key: str) -> None:
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "Inditex"
```

**Padrão de search com BrandSearchResult.error como canal de falha** (padrão `_search_one` em `factory.py` linhas 89–102):
```python
async def search(self, query: str, max_results: int = 10, **kwargs) -> BrandSearchResult:
    from services.brand_service import brand_service
    brand = brand_service.get_brand(self.brand_key)
    if not brand:
        return BrandSearchResult(
            brand_key=self.brand_key, brand_name=self.brand_key,
            error="Marca não encontrada"
        )
    try:
        products = await self._fetch_products(brand.domain, query, max_results)
        return BrandSearchResult(
            brand_key=self.brand_key, brand_name=brand.brand_name,
            products=products, total_found=len(products)
        )
    except Exception as exc:
        return BrandSearchResult(
            brand_key=self.brand_key, brand_name=brand.brand_name,
            error=str(exc)
        )
```

**Contrato mínimo de SearchProductResult** (`backend/core/models.py`, conforme RESEARCH.md):
```python
SearchProductResult(
    brand="zara",
    product_name="...",   # título real, não vazio
    url="https://www.zara.com/br/...",  # domínio zara.com/br
    price_full=499.0,     # float > 0
    image_url="...",      # quando disponível; None aceitável
)
```

---

### `backend/services/engines/factory.py` — acrescentar branch inditex (APENAS em GO)

**Analog:** branches `sfcc` e `wake` já existentes no mesmo arquivo

**Lazy import pattern** (linhas 48–57 do arquivo):
```python
# D-09 (Phase 31 — SFCC now live): lazy import para preservar circular-import safety
if engine_type == "sfcc":
    from services.engines.sfcc_engine import SFCCEngine  # noqa: PLC0415
    return SFCCEngine(brand_key)

# D-09 (Phase 32 — Wake now live): mesmo padrão
if engine_type == "wake":
    from services.engines.wake_engine import WakeEngine  # noqa: PLC0415
    return WakeEngine(brand_key)
```

**Branch a acrescentar (após o bloco wake):**
```python
# D-08 (Phase 39 — Inditex/Zara — só em GO): mesmo padrão de lazy import
if engine_type == "inditex":
    from services.engines.inditex_engine import InditexEngine  # noqa: PLC0415
    return InditexEngine(brand_key)
```

---

## Shared Patterns

### Hermetismo de testes (sem I/O de arquivo, sem rede)
**Fonte:** `backend/tests/test_vtex_brand_onboarding_contract.py` linhas 36–64
**Aplicar a:** `test_hugoboss_category_mapping.py`, `test_hugoboss_vtex_scan.py`
```python
svc = BrandManagerService.__new__(BrandManagerService)
svc.brands = {}
svc.last_modified = 0
svc.updated_event = asyncio.Event()
svc._check_reload = unittest.mock.MagicMock()
# Popula brands manualmente — zero I/O
svc.brands["hugoboss"] = DynamicBrand(...)
```

### Monkeypatch de brand_service no módulo category_mapping
**Fonte:** `backend/tests/test_vtex_brand_onboarding_contract.py` linhas 196–198
**Aplicar a:** qualquer teste que chame `resolve_category_for_brands` ou `get_canonical_categories`
```python
with unittest.mock.patch.object(category_mapping_module, "brand_service", svc):
    result = resolve_category_for_brands("camisas", ["hugoboss"])
```

### Detecção de bloqueio em spikes
**Fonte:** `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` linhas 80–91
**Aplicar a:** `experiment.py` do spike 010
```python
def _detect_block(html: str, status: Optional[int]) -> list[str]:
    signals: list[str] = []
    if status == 403:
        signals.append("http_status_403")
    if "access denied" in html.lower():
        signals.append("access_denied_text")
    if len(html.encode("utf-8")) < 1000:
        signals.append("html_below_1000_bytes")
    return signals
```

### Cleanup de recursos Playwright (finally)
**Fonte:** `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` linhas 178–184
**Aplicar a:** `experiment.py` do spike 010
```python
finally:
    for handle in (page, context, browser):
        try:
            if handle:
                handle.close()
        except Exception:
            pass
```

---

## No Analog Found

Nenhum arquivo desta phase ficou sem analog — toda a infraestrutura reutiliza padrões existentes.

| Arquivo | Observação |
|---------|-----------|
| `backend/services/engines/inditex_engine.py` (GO) | O **body de `_fetch_products`** é net-new e depende do que o spike 010 revelar (JSON-LD vs XHR vs HTML parsing). O analog de WakeEngine cobre estrutura e contrato; a lógica de extração específica da Zara não tem analog ainda. |

---

## Anti-Padrões Documentados (a evitar)

| Anti-padrão | Onde fica a regra | Consequência |
|-------------|------------------|--------------|
| Salvar `vtex_fq_path` como URL completa (sem `urlparse(...).path`) | `onboard_vtex_brands.py` linha 329 ("Pitfall 3 DEFUSED") | `resolve_category_for_brands` constrói URL inválida: `"https://..." + "https://..."` |
| Passar `"hugoboss.com.br"` (sem `www.`) | STATE.md `[onboarding-live/2026-06-25]` | Requisição ao endpoint VTEX falha ou retorna 0 categorias |
| Usar `section=WOMAN` na query de busca da Zara | D-07 / CAT-01 | Retorna produtos femininos; violação do filtro masculino |
| Commitar `inditex_engine.py` antes do veredito GO | D-08/D-09 | Código incompleto em `backend/`; EngineFactory pode falhar com `NotImplementedError` |
| Testar Zara com HTTP direto (requests/aiohttp) | Spike 003 — 403 documentado | Sempre 403; usar apenas Playwright + stealth |
| Hardcodar paths da Hugo Boss em `_RAW_CATEGORIES` | D-01 | Viola separação marcas da casa vs. concorrentes; dificulta manutenção |

---

## Metadata

**Escopo de busca de analogs:** `backend/scripts/`, `backend/tests/`, `backend/services/engines/`, `.planning/spikes/`
**Arquivos lidos:** `onboard_vtex_brands.py`, `factory.py`, `test_vtex_brand_onboarding_contract.py`, `spikes/008/experiment.py`, `wake_engine.py`, `category_mapping.py`
**Data do mapeamento:** 2026-06-26
