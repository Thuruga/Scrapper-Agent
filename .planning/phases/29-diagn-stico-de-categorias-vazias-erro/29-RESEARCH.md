# Phase 29: Diagnóstico de Categorias Vazias/Erro - Research

**Researched:** 2026-06-22
**Domain:** VTEX Category Health Diagnostic — Backend probe service + FastAPI endpoint + React UI panel
**Confidence:** HIGH (all critical claims verified directly from codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Cobre **todas as marcas** via `list_brands(active_only=False)` — bypassa o chokepoint is_active deliberadamente (diagnóstico, não busca).
- **D-02:** Marcas não-VTEX / sem mapeamento aparecem com marcador especial "sem probe", não são verificadas.
- **D-03:** Marcas inativas sinalizadas visualmente de forma distinta (não confundir com "erro") — padrão SettingsPage opacity 0.55.
- **D-04:** Gatilho on-demand: botão por marca + "Diagnosticar todas" no topo. Resultado sempre fresco.
- **D-05:** Execução **síncrona** — endpoint dispara probes concorrentes e retorna o relatório completo na resposta.
- **D-06:** Resultados **efêmeros** — sem persistência/cache/timestamp.
- **D-07:** Probe dedicado e leve. NÃO reusar `engine.search()`. NÃO usar fallback full-text (L833 em `search()`).
- **D-08:** Requisição **crua** — sem retries, sem fallback de domínio estável por-categoria, sem Playwright em 403. NÃO passar por `_request_json`.
- **D-09:** Sinal ok/vazia pela primeira página (`_from=0`). Lista não-vazia → ok; lista vazia + HTTP 200 → vazia. Lê header `resources` para contagem total.
- **D-10:** Resolve base URL **uma vez por marca** antes dos probes (reusar lógica de auto-discovery existente, não auto-heal por-categoria).
- **D-11:** Tudo que não é HTTP 200 + JSON válido → `erro`, com http_status + error_detail.
- **D-12:** Mapping stale (200 + 0 produtos) → `vazia`. A URL probada é exposta no painel.
- **D-13:** Nova aba "Diagnóstico" (ex: "Saúde de Categorias") no sidebar + `renderTab` switch.
- **D-14:** Layout agrupado por marca com chip de status (ok/vazia/erro).
- **D-15:** Linha expansível por categoria — chip visível, detalhes (http_status, error_detail, URL) ao expandir.
- **D-16:** Botão "Diagnosticar" por marca + "Diagnosticar todas" com estado de loading.

### Claude's Discretion

- Resolução exata path→URL por marca/categoria (via `resolve_category_for_brands`, tratamento de `vtex_fq` vs path amigável fica ao planner).
- Grau de concorrência (semáforo / `asyncio.gather` com limite).
- Forma exata do marcador D-02 no contrato e na UI.
- Quantos itens pedir na página 0 (`_to=0` vs `_to=9`).
- Nome/forma exata do endpoint e dos modelos Pydantic.
- Filosofia de teste offline/determinístico.

### Deferred Ideas (OUT OF SCOPE)

- Persistência/cache de resultados + agendamento em background.
- Probe de motores não-VTEX (Shopify, marketplaces virtuais, engine "unknown").
- Validar path contra árvore de categorias para distinguir stale de vazia sazonal.
- Auto-ação sobre categorias vazias/erro.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DIAG-01 | O sistema identifica e reporta, por marca/motor, categorias sem produtos (vazias) e categorias com erro, distinguindo explicitamente "vazia" de "erro", com status + código HTTP + detalhe. | Probe dedicado via aiohttp direto (não `_request_json`); classificador three-state; header `resources` para contagem. |
| DIAG-02 | Usuário pode visualizar um relatório/painel de saúde das categorias por marca/motor (status ok / vazia / erro). | Nova aba `renderTab` + sidebar; componente agrupado por marca com chips + linha expansível; `ApiClient` com novo método GET. |
</phase_requirements>

---

## Summary

Phase 29 entrega um serviço de diagnóstico de saúde de categorias VTEX. O backend expõe um endpoint síncrono que, para cada marca, resolve o base URL uma vez (D-10, reusando `fetch_categories` / `_discover_account_from_html`), depois dispara probes `aiohttp` crus e concorrentes (sem a camada resiliente de `_request_json`) para cada categoria mapeada, classifica o resultado em `ok` / `vazia` / `erro` e retorna tudo na resposta HTTP. O frontend adiciona uma nova aba ao `renderTab` switch e ao sidebar de `App.tsx`, com um componente de lista agrupada por marca e chips de status expansíveis.

A distinção central desta phase em relação ao scraper existente é **a negação intencional da resiliência**: onde `_request_json` tem retries, fallback de domínio estável e Playwright em 403, o probe do diagnóstico quer exatamente o status bruto — capturado com `aiohttp` diretamente. A resolução de domínio uma-vez-por-marca (D-10) é a única concessão necessária para evitar falsos positivos sistêmicos em lojas headless/FastStore.

A terminologia de status nos critérios de sucesso do ROADMAP usa inglês (`ok`/`empty`/`error`); o CONTEXT.md usa português (`ok`/`vazia`/`erro`) para a UI. A recomendação é usar os valores em **inglês no contrato de API** (enum no Pydantic: `"ok"`, `"empty"`, `"error"`) e os rótulos em português apenas na camada de exibição do frontend — alinhando com o padrão dos critérios de sucesso e garantindo neutralidade de idioma na API.

**Primary recommendation:** Criar `services/category_diagnostic_service.py` com a lógica de probe + classificação, `api/routes_diagnostic.py` com a rota fina GET (síncrona, não background task), e `frontend/src/pages/DiagnosticPage.tsx` com o painel — seguindo o padrão de três camadas existente.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Resolução de base URL por marca | API / Backend | — | Envolve I/O de rede (HTML scraping do domínio público); não pertence à camada de rota |
| Probe HTTP cru por categoria | API / Backend | — | I/O de rede; classificação é lógica de negócio |
| Classificação three-state | API / Backend | — | Regra de negócio pura; deve ser testável offline |
| Enumeração de marcas e categorias | API / Backend | — | Lê brand_service + category_mapping |
| Endpoint síncrono de diagnóstico | API / Backend | — | Rota fina que delega ao serviço |
| Painel de saúde (UI) | Browser / Client | — | React component; recebe JSON pronto do endpoint |
| Chips de status + linha expansível | Browser / Client | — | Presentational; sem lógica de negócio |
| Trigger de loading / botão por marca | Browser / Client | — | Estado local de UI; abortController não necessário (síncrono) |

---

## Standard Stack

### Core (já no projeto — sem instalações adicionais)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | 3.13.3 [VERIFIED: instalado] | HTTP client para o probe cru | Já usado em VtexApiClient; AsyncSession do aiohttp é a forma direta sem a camada `_request_json` |
| curl_cffi | 0.15.0 [VERIFIED: instalado] | AsyncSession para auto-discovery (fetch_categories) | Impersonates Chrome; já usado em fetch_categories para o HTML scraping de auto-discovery |
| FastAPI (já no projeto) | — | Endpoint síncrono (async def) | Padrão do projeto |
| Pydantic v2 (já no projeto) | — | Modelos de resposta | Padrão do projeto |
| asyncio | stdlib | gather + Semaphore para concorrência limitada | Já usado em todo o backend |
| pytest | 9.0.3 [VERIFIED: instalado] | Framework de testes | Projeto usa pytest; testes offline com monkeypatch/MagicMock |
| React 19 + TypeScript + Tailwind | — | Frontend | Padrão do projeto |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Semaphore | stdlib | Limitar concorrência dos probes (D-05) | Evitar rate limit VTEX com muitas marcas simultâneas |
| sonner (já no projeto) | — | Toast de erro na UI | Padrão de erro no frontend (ver CrossMarketplacePage) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| aiohttp direto | httpx | httpx é mais moderno mas aiohttp já é dependência do projeto; evitar nova dependência |
| asyncio.gather com semáforo | asyncio.TaskGroup | TaskGroup (Python 3.11+) mais ergonômico mas o projeto usa gather em todo lugar; manter consistência |

**Installation:** Nenhuma nova dependência necessária — tudo já está no projeto.

---

## Package Legitimacy Audit

> Nenhum pacote novo é instalado nesta phase. Todos os pacotes usados (aiohttp, curl_cffi, pytest, FastAPI, Pydantic, React) já são dependências estabelecidas do projeto.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
[Frontend: DiagnosticPage]
  |-- "Diagnosticar" button click
  v
GET /diagnostic/brands/{brand_key}     OR     GET /diagnostic/all
  |
  v
[api/routes_diagnostic.py]  (rota fina — zero lógica de negócio)
  |
  v
[services/category_diagnostic_service.py]
  |
  +-- brand_service.list_brands(active_only=False)          → lista todas as marcas
  |
  +-- engine_factory.get_engine(brand_key).get_engine_name()  → filtra VTEX vs "sem probe"
  |
  +-- Para cada marca VTEX:
  |     |
  |     +-- resolve_base_url(brand) UMA VEZ                  → stable_domain (D-10)
  |     |     (via VtexApiClient.fetch_categories ou
  |     |      _discover_account_from_html se HTML no público)
  |     |
  |     +-- enumerate_categories(brand_key)                  → slugs com path/label
  |     |     (via _RAW_CATEGORIES + brand.mappings)
  |     |
  |     +-- asyncio.gather(*[probe(cat) for cat in cats],    → concorrência limitada (D-05)
  |           semaphore=Semaphore(5))
  |               |
  |               v
  |           [probe_category(base_url, path)]               → raw aiohttp GET (D-08)
  |               |  - sem retry
  |               |  - sem stable-domain-fallback por-categoria
  |               |  - sem Playwright
  |               |  - captura http_status, Content-Type, body
  |               v
  |           [classify(http_status, body, content_type)]    → "ok"|"empty"|"error"
  |               - 200 + JSON list não-vazia → "ok"
  |               - 200 + JSON list vazia     → "empty"
  |               - 200 + HTML body           → "error" (error_detail: "HTML instead of JSON")
  |               - 4xx/5xx/timeout/network   → "error"
  |               - lê header "resources" para total_count
  |
  +-- Para marcas não-VTEX ou sem mapeamento:
        → marcador especial (status: "no_probe")
  |
  v
DiagnosticReportResponse (Pydantic)
  → [Frontend: renderiza cards por marca, chips de status, linhas expansíveis]
```

### Recommended Project Structure

```
services/
├── category_diagnostic_service.py   # novo: probe + classify + enumerate
api/
├── routes_diagnostic.py             # novo: rota fina GET; inclui no __init__.py
frontend/src/
├── pages/
│   └── DiagnosticPage.tsx           # novo: painel agrupado por marca
└── api/
    └── client.ts                    # estender: adicionar método getDiagnostic(brandKey?)
```

### Pattern 1: Probe HTTP cru (D-08) — a negação intencional de _request_json

**What:** Usar `aiohttp.ClientSession.get()` diretamente, sem passar por `_request_json` (que tem retry, stable-domain-fallback, Playwright em 403).
**When to use:** Sempre no diagnóstico — qualquer resiliência esconderia o status real.

```python
# Source: verificado em services/vtex_api_scraper.py (padrão aiohttp do projeto)
import aiohttp
import asyncio

async def probe_category(
    session: aiohttp.ClientSession,
    base_url: str,
    path: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """
    Probe cru: 1 GET, sem retry, captura status real.
    Retorna dict com: status ("ok"|"empty"|"error"), http_status,
    error_detail, total_count, probed_url.
    """
    # _from=0&_to=9: pede 10 itens — suficiente para sinal de presença
    # sem paginar; lê resources header para total real
    path_clean = path.lstrip("/")
    url = f"{base_url}/api/catalog_system/pub/products/search/{path_clean}?_from=0&_to=9"

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                http_status = resp.status
                content_type = resp.headers.get("Content-Type", "")

                if http_status != 200:
                    return {
                        "status": "error",
                        "http_status": http_status,
                        "error_detail": f"HTTP {http_status}",
                        "total_count": None,
                        "probed_url": url,
                    }

                if "text/html" in content_type:
                    return {
                        "status": "error",
                        "http_status": http_status,
                        "error_detail": "HTML instead of JSON (possible headless/WAF block)",
                        "total_count": None,
                        "probed_url": url,
                    }

                try:
                    body = await resp.json(content_type=None)
                except Exception as parse_err:
                    return {
                        "status": "error",
                        "http_status": http_status,
                        "error_detail": f"JSON parse error: {parse_err}",
                        "total_count": None,
                        "probed_url": url,
                    }

                # Lê resources header: formato "x-y/total"
                total_count = None
                resources_header = resp.headers.get("resources", "")
                if "/" in resources_header:
                    try:
                        total_count = int(resources_header.split("/")[-1])
                    except ValueError:
                        pass

                if isinstance(body, list) and len(body) > 0:
                    return {
                        "status": "ok",
                        "http_status": 200,
                        "error_detail": None,
                        "total_count": total_count,
                        "probed_url": url,
                    }
                else:
                    return {
                        "status": "empty",
                        "http_status": 200,
                        "error_detail": None,
                        "total_count": total_count or 0,
                        "probed_url": url,
                    }

        except asyncio.TimeoutError:
            return {
                "status": "error",
                "http_status": None,
                "error_detail": "Timeout",
                "total_count": None,
                "probed_url": url,
            }
        except Exception as exc:
            return {
                "status": "error",
                "http_status": None,
                "error_detail": f"Network error: {exc}",
                "total_count": None,
                "probed_url": url,
            }
```

### Pattern 2: Resolução de Base URL uma vez por marca (D-10)

**What:** Chamar `VtexApiClient.fetch_categories(domain)` — que já implementa o auto-discovery público→estável — ou usar `_discover_account_from_html` diretamente para inferir o `stable_domain`. O resultado é cacheado na memória local do service call (não persistido, D-06).

**Comportamento exato verificado em vtex_api_scraper.py L46-130:**
1. Tenta `https://{domain}/api/catalog_system/pub/category/tree/{depth}`.
2. Se retorna JSON válido → domínio público funciona, usa-o.
3. Se retorna HTML (loja headless/FastStore) → extrai `account_name` de `_discover_account_from_html(domain, response.text)` → forma `{account_name}.vtexcommercestable.com.br`.
4. Tenta o fallback estável; se funcionar → usa o domínio estável.

**Para o diagnóstico:** não é necessário chamar `fetch_categories` completo (que retorna a árvore). Basta o sub-passo de descoberta do domínio estável — mas reusar `fetch_categories` é a opção mais segura e já testada. O resultado prático é: `base_url = "https://{domain}"` OU `"https://{account_name}.vtexcommercestable.com.br"` — este base_url é usado em todos os probes daquela marca.

**Falso positivo sistêmico (D-10) que o planner deve evitar:**
- Loja headless/FastStore: `https://{public_domain}/api/catalog_system/pub/products/search/roupas/camisas` retorna HTML 200 (não JSON).
- Sem a resolução de domínio, o probe classificaria TODAS as categorias dessa marca como `erro`.
- Com a resolução, o probe usa `https://{account_name}.vtexcommercestable.com.br/api/...` e obtém o JSON correto.

### Pattern 3: Enumeração de categorias por marca

**What:** Para uma dada marca, listar todos os slugs canônicos que ela tem mapeados.
**How:** Combinar `_RAW_CATEGORIES` (hardcoded) + `brand.mappings` (DynamicBrand).

```python
# Source: verificado em services/category_mapping.py
from services.category_mapping import _CATEGORY_INDEX
from services.brand_service import brand_service

def get_brand_category_paths(brand_key: str) -> list[dict]:
    """Retorna lista de {slug, path, label, vtex_fq} para a marca."""
    bk = brand_key.lower()
    brand_data = brand_service.get_brand(bk)
    if not brand_data:
        return []

    results = []
    # 1. Hardcoded (_RAW_CATEGORIES via _CATEGORY_INDEX)
    for slug, cat in _CATEGORY_INDEX.items():
        if bk in cat.brands:
            info = cat.brands[bk]
            results.append({
                "slug": slug,
                "label": cat.label,
                "path": info.path,        # ex: "/roupas/camisas"
                "vtex_fq": info.vtex_fq,  # ex: "C:/480/507/"
            })
    # 2. Dinâmicos (DynamicBrand.mappings)
    for mapping in brand_data.mappings:
        if not any(r["slug"] == mapping.canonical_slug for r in results):
            results.append({
                "slug": mapping.canonical_slug,
                "label": mapping.label,
                "path": mapping.vtex_fq_path,  # pode ser "C:/..." ou "/path"
                "vtex_fq": mapping.vtex_fq_path,
            })
    return results
```

**Atenção ao `vtex_fq_path` nos mapeamentos dinâmicos:** O campo `vtex_fq_path` em `CategoryMapping` pode conter tanto um path amigável (`/roupas/polos`) quanto um filtro VTEX (`C:/480/523/`). A `resolve_category_for_brands` já lida com isso: se começa com `/` → é path de URL; se começa com `C:/` ou `B:` → é fq filter (não gera URL de categoria direto). O probe deve usar o **path amigável** na URL. Para mapeamentos com fq puro sem path amigável, o planner deve decidir se (a) pula esse mapeamento no probe ou (b) usa o endpoint com `?fq=C:/...` em vez de path na URL.

**Recomendação:** Usar a URL com path amigável quando disponível; para fq puro, usar `?fq={vtex_fq}` no probe URL (endpoint VTEX aceita ambos conforme `search()` L719).

### Pattern 4: Concorrência limitada (D-05)

**What:** `asyncio.gather` com `asyncio.Semaphore` para limitar probes simultâneos.
**Recomendação:** Semáforo de 5 por marca (6 categorias/marca → todos concorrentes mas com cap); para "Diagnosticar todas" (N marcas × 6 cats), semáforo global de 10-15.

```python
# Source: padrão asyncio.gather já usado em scrape_category_paged L659
async def run_brand_probes(session, base_url, categories, semaphore):
    tasks = [probe_category(session, base_url, cat["path"], semaphore) for cat in categories]
    return await asyncio.gather(*tasks)
```

### Pattern 5: Endpoint de diagnóstico (rota fina)

**What:** `GET /diagnostic/brands/{brand_key}` e `GET /diagnostic/all` — síncrono (async def, sem BackgroundTasks).
**How:** Segue o padrão de `routes_category.py` mas sem job_id/WebSocket (D-05 = síncrono).

```python
# Source: padrão routes_category.py e api/__init__.py
from fastapi import APIRouter, HTTPException
from services.category_diagnostic_service import run_brand_diagnostic, run_all_brands_diagnostic

router = APIRouter()

@router.get("/diagnostic/brands/{brand_key}")
async def diagnose_brand(brand_key: str):
    result = await run_brand_diagnostic(brand_key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Marca '{brand_key}' não encontrada.")
    return result

@router.get("/diagnostic/all")
async def diagnose_all():
    return await run_all_brands_diagnostic()
```

**Registrar em `api/__init__.py`:** importar e incluir `diagnostic_router` no `api_router` (que já tem `Depends(verify_api_key)`).

### Pattern 6: Modelos Pydantic de resposta

```python
# Source: padrão core/models.py (DynamicBrand, BrandSearchResult)
from pydantic import BaseModel
from typing import Optional, List, Literal

class CategoryDiagnosticResult(BaseModel):
    slug: str
    label: str
    status: Literal["ok", "empty", "error", "no_probe"]
    http_status: Optional[int] = None
    error_detail: Optional[str] = None
    total_count: Optional[int] = None
    probed_url: Optional[str] = None

class BrandDiagnosticResult(BaseModel):
    brand_key: str
    brand_name: str
    domain: str
    is_active: bool
    engine: str
    categories: List[CategoryDiagnosticResult]

class DiagnosticReportResponse(BaseModel):
    brands: List[BrandDiagnosticResult]
```

**Nota sobre `engine`:** `engine_factory.get_engine(brand_key)` retorna um objeto `BaseEngine`; use `getattr(engine, 'get_engine_name', lambda: 'unknown')()` para obter a string. Alternativamente, leia `brand_data.engine` diretamente de `DynamicBrand` (campo `engine: Optional[str] = "vtex"` em `DynamicBrandCreate`).

### Pattern 7: Frontend — nova aba e ApiClient

**renderTab switch (App.tsx L2107-2117):** adicionar `case 'diagnostic': return <DiagnosticPage brands={brands} />;`

**sidebar nav (App.tsx L2135-2173):** adicionar `SidebarItem` com ícone `HeartPulse` ou `Activity` (Lucide) entre "Monitor de Categorias" e "Comparativa" — posição de observabilidade.

**Cabeçalho (L2183-2190):** adicionar `activeTab === 'diagnostic' ? 'Saúde de Categorias' :` na expressão do `<h1>`.

**ApiClient (client.ts):** padrão GET sem body:
```typescript
static getDiagnostic(brandKey?: string) {
  const endpoint = brandKey
    ? `/diagnostic/brands/${encodeURIComponent(brandKey)}`
    : '/diagnostic/all';
  return this.request<any>(endpoint);
}
```

**Tratamento de loading:** estado local `loading: Record<string, boolean>` no componente — `{ [brand_key]: true }` durante o fetch, false ao concluir.

### Anti-Patterns to Avoid

- **Usar `_request_json` no probe:** Tem retry, fallback de domínio estável, Playwright — esconderia exatamente o status que o diagnóstico precisa medir (D-08).
- **Usar `VTEXEngine.search()` no probe:** Tem fallback full-text (L833) que re-busca sem path de categoria — mascararia categoria vazia/erro (D-07).
- **Lançar como BackgroundTask:** D-05 é síncrono; não usar `background_tasks.add_task`. O timeout do aiohttp no probe garante que o endpoint responda em tempo razoável.
- **Auto-heal de domínio por categoria:** D-10 é 1x por marca, não por categoria — se o probe de uma categoria específica retorna HTML, é `erro`, não trigger de auto-discovery.
- **Misturar status em português no contrato de API:** Usar inglês no enum Pydantic (`"ok"`, `"empty"`, `"error"`, `"no_probe"`); usar PT-BR apenas nos rótulos de display no frontend.
- **Usar `_to=0` como parâmetro:** VTEX interpreta `_to=0` como "até o item 0" → retornaria no máximo 1 item. Usar `_to=9` (10 itens) como sinal de presença é mais seguro.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auto-discovery domínio estável | Lógica nova de regex/scraping | `VtexApiClient.fetch_categories` + `_discover_account_from_html` | Já testado em produção com headless/FastStore |
| Enumeração de categorias por marca | Parse direto de `brands.json` | `_CATEGORY_INDEX` + `brand.mappings` (padrão de `category_mapping.py`) | Index já construído; inclui dinâmicos |
| HTTP client para probe | `requests.get` (síncrono) | `aiohttp.ClientSession` (já no projeto) | Síncrono bloquearia o event loop do FastAPI |
| Loading state na UI | Polling/WebSocket | Estado local React `useState` + flag por marca | D-05 é síncrono; a resposta chega na mesma chamada |
| Chips de status coloridos | CSS custom | Classes Tailwind (`bg-green-500`, `bg-yellow-500`, `bg-red-500`) | Stack do projeto |

**Key insight:** O probe VTEX mais simples (1 GET por categoria) já é suficiente para distinguir os 3 estados. Qualquer complexidade adicional (retry, fallback, cache) contradiz a D-08/D-06.

---

## Codebase Verification Findings

### 1. `_request_json` (vtex_api_scraper.py L228-294) — comportamento exato verificado

O método `_request_json` tem **três camadas de resiliência que o probe NÃO deve usar**:
1. **Loop de retry** (`for attempt in range(settings.MAX_RETRIES)`) com `asyncio.sleep(2 ** attempt)` em 5xx.
2. **Fallback de domínio estável por chamada**: se recebe HTML com status 200, chama `_ensure_account_resolved` e seta `use_stable_fallback = True` — reescreve a URL de todas as chamadas seguintes.
3. **Playwright fallback em 403/401**: chama `browser_manager.fetch_html(current_url)` e tenta parsear o HTML como JSON.

**Minimal raw HTTP call** que o probe deve usar: `session.get(url, timeout=...)` direto no `aiohttp.ClientSession` — sem passar por qualquer método de `VtexApiClient`. A sessão aiohttp pode ser criada no service de diagnóstico com headers mínimos:

```python
headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; DiagnosticProbe/1.0)",
}
async with aiohttp.ClientSession(headers=headers) as session:
    # probes aqui
```

### 2. `scrape_category_paged` — header `resources` (L546-559) verificado

O header `resources` já é lido em `scrape_category_paged` mas seu uso está comentado:
```python
# Nao enviamos mais o total de produtos para evitar confusao de paridade
# total_produtos = int(res_header.split("/")[-1])
```
O formato confirmado é `"x-y/total"` (ex: `"0-9/47"`). O total está após a última `/`. O probe deve parsear `int(resources_header.split("/")[-1])` com try/except.

**URL exata do endpoint search-by-path** (confirmada em L503 e L522):
```
https://{domain}/api/catalog_system/pub/products/search/{path}?_from=0&_to=9
```
Onde `path` é o path relativo sem `/` inicial (L500: `path = parsed.path.strip("/")`).

### 3. `search()` fallback full-text (L833) — confirmado

```python
# L830-838 de vtex_api_scraper.py
if not products and category_path is not None:
    logger.info(f"[{brand_key}] category_path '{category_path}' retornou 0 produtos; "
                f"fallback full-text para query '{query}'.")
    products, last_error = await _run_paging(None)
```
Este fallback re-busca sem o path de categoria (usando a query full-text no endpoint `/search/{query}`). Se o probe usasse `search()`, uma categoria vazia ou com path inválido seria mascarada por resultados via busca textual — confirmando D-07.

### 4. `resolve_category_for_brands` (category_mapping.py L191) — assinatura exata verificada

```python
def resolve_category_for_brands(
    category_slug: str,
    brand_keys: List[str],
) -> Dict[str, dict]:
```
Retorna `{brand_key: {"url": str, "path": str, "label": str}}`.

**Caveat crítico** (L227-233): para mapeamentos dinâmicos com `vtex_fq_path` que começa com `C:/` ou `B:` (não com `/`), a função NÃO consegue gerar uma URL de categoria amigável — o bloco `pass` está lá explicitamente. Nesses casos, o probe deve usar o endpoint com `?fq=`:
```
/api/catalog_system/pub/products/search?fq=C:/480/507/&_from=0&_to=9
```
O formato `?fq=` está documentado em `search()` L719 do mesmo arquivo.

### 5. `engine_factory.get_engine` (factory.py) — comportamento exato verificado

```python
engine_type = getattr(brand_data, "engine", "vtex")
if engine_type == "shopify":
    return ShopifyEngine(brand_key)
return VTEXEngine(brand_key)  # default — inclui "unknown" engine!
```

**Atenção:** brands com `engine="unknown"` também retornam `VTEXEngine` do factory — não há tratamento especial. Para D-02, o serviço de diagnóstico deve verificar o campo `brand_data.engine` diretamente, não confiar no factory:
```python
engine_type = getattr(brand_data, "engine", "vtex")
is_vtex_probe_eligible = (engine_type == "vtex")
```

### 6. `list_brands(active_only=False)` (brand_service.py L207) — verificado

```python
def list_brands(self, active_only: bool = False) -> List[DynamicBrand]:
    self._check_reload()
    brands = list(self.brands.values())
    if active_only:
        return [b for b in brands if b.is_active]
    return brands
```
Chamar `list_brands()` sem argumento (ou `active_only=False`) retorna todas as marcas incluindo inativas. D-01 está correto.

### 7. `DynamicBrand` — campos relevantes verificados (core/models.py)

```python
class DynamicBrand(DynamicBrandCreate):
    mappings: List[CategoryMapping] = Field(default_factory=list)
    is_active: bool = True

class DynamicBrandCreate(BaseModel):
    brand_key: str
    brand_name: str
    domain: str          # sem https://, sem trailing /
    engine: Optional[str] = "vtex"
    # ...

class CategoryMapping(BaseModel):
    canonical_slug: str    # ex: "polos", "camisas"
    vtex_fq_path: str      # ex: "C:/1/2/" OU "/roupas/polos"
    label: str             # ex: "Polos Masculinas"
```

### 8. Aba/sidebar App.tsx — posições exatas verificadas

- `renderTab` switch: L2107-2117. Adicionar `case 'diagnostic':` antes do `default`.
- Sidebar nav: L2135-2173. Adicionar `SidebarItem` antes do `<div className="sidebar-spacer" />` (L2166).
- `<h1>` do header: L2183-2190. Adicionar case para `'diagnostic'`.
- Opacity 0.55 para inativas: L1705 — `style={b.is_active === false ? { opacity: 0.55 } : undefined}` aplicado no `.brand-info`. Replicar no `DiagnosticPage`.
- `MonitoredCategoriesPage` em L1754: padrão com `useState`, `useEffect` para fetch inicial, lista de cards.

### 9. ApiClient (client.ts) — padrão verificado

Todos os métodos são estáticos. `request<T>(endpoint, options, signal?)` é o core. Não há lógica de negócio no client — apenas HTTP + headers. Seguir o padrão de `getHistoryList()` para o GET sem body:
```typescript
static getDiagnostic(brandKey?: string) {
  const endpoint = brandKey
    ? `/diagnostic/brands/${encodeURIComponent(brandKey)}`
    : '/diagnostic/all';
  return this.request<DiagnosticReportResponse>(endpoint);
}
```

---

## Common Pitfalls

### Pitfall 1: Falso positivo sistêmico em lojas headless/FastStore

**What goes wrong:** Probe faz GET no domínio público (`www.marca.com.br`). A loja retorna HTML 200 (não JSON) em todas as URLs de API — porque é headless/FastStore. O probe classifica TODAS as categorias como `erro`.
**Why it happens:** Lojas headless/FastStore servem o SPA no domínio público; as APIs VTEX ficam no domínio estável `{account}.vtexcommercestable.com.br`.
**How to avoid:** Implementar D-10 — chamar `fetch_categories(domain)` (ou `_discover_account_from_html`) UMA VEZ por marca ANTES de disparar os probes. Se retornou HTML, o `account_name` extraído é usado como base URL estável para todos os probes daquela marca.
**Warning signs:** Múltiplas categorias da mesma marca com `error_detail: "HTML instead of JSON"`.

### Pitfall 2: engine="unknown" não filtrado pelo factory

**What goes wrong:** `engine_factory.get_engine("unknown_brand")` retorna `VTEXEngine` mesmo para `engine="unknown"` (o factory não tem caso para "unknown"). O probe é disparado contra uma loja não-VTEX.
**Why it happens:** Factory só tem cases para "shopify" e marketplaces virtuais; qualquer outro engine cai no default VTEX.
**How to avoid:** No serviço de diagnóstico, verificar `brand_data.engine` ANTES de chamar o factory. Somente `engine == "vtex"` recebe probe real.
**Warning signs:** Brand com `engine="unknown"` aparecendo com resultados de probe (deveria ter `status: "no_probe"`).

### Pitfall 3: vtex_fq_path sem path amigável

**What goes wrong:** `resolve_category_for_brands` recebe um slug cujo mapeamento dinâmico tem `vtex_fq_path = "C:/480/507/"`. A função retorna `{"url": "https://www.marca.com.br/C:/480/507/", "path": "C:/480/507/"}` — URL inválida.
**Why it happens:** O campo `vtex_fq_path` pode conter tanto paths amigáveis quanto filtros VTEX fq. Quando é fq, não há path de URL disponível.
**How to avoid:** Verificar se `vtex_fq_path.startswith("/")`. Se não, usar o endpoint com `?fq=` em vez de path na URL. Ex: `/api/catalog_system/pub/products/search?fq=C:/480/507/&_from=0&_to=9`.
**Warning signs:** `probed_url` contendo `C:/` ou `B:` no path (ao invés de query param).

### Pitfall 4: Timeout de endpoint longo com muitas marcas

**What goes wrong:** "Diagnosticar todas" com N marcas × 6 categorias = 30+ probes, cada um com timeout de 10s. Se probes forem serializados → 5 minutos de espera. Se totalmente paralelos → potencial rate limit.
**Why it happens:** D-05 é síncrono; o FastAPI espera o async def completar.
**How to avoid:** Semáforo global de 10-15 para o "Diagnosticar todas" + timeout de 8-10s por probe. No frontend, mostrar loading state adequado para latência esperada (10-30s para todas as marcas).
**Warning signs:** Requests HTTP chegando em cluster na VTEX ao mesmo tempo; 429 responses nos probes.

### Pitfall 5: Misturar os dois contratos de status

**What goes wrong:** ROADMAP usa `ok`/`empty`/`error` (inglês); CONTEXT.md usa `ok`/`vazia`/`erro` (PT-BR). Se o Pydantic enum usar PT-BR mas o frontend esperar inglês (ou vice-versa), os chips de status ficam incorretos.
**How to avoid:** Usar inglês (`"ok"`, `"empty"`, `"error"`) no enum Pydantic e no JSON de API. Mapear para PT-BR apenas no componente React (`const LABELS = { ok: "OK", empty: "Vazia", error: "Erro" }`).

### Pitfall 6: resources header ausente = total_count null (não erro)

**What goes wrong:** Se o header `resources` não estiver presente (ex: categoria com 0 produtos, ou VTEX não enviar), o probe falha ao parsear e marca a categoria como erro.
**Why it happens:** Assumir que `resources` sempre existe.
**How to avoid:** `resources_header = resp.headers.get("resources", "")` com fallback `""`. `total_count = None` se ausente ou não parseável — não é erro, é dado indisponível.

---

## Edge Case Classification Matrix

| Cenário | HTTP Status | Body | Content-Type | → status | error_detail |
|---------|-------------|------|--------------|----------|-------------|
| Categoria com produtos | 200 | list não-vazia | application/json | `ok` | null |
| Categoria vazia / stale | 200 | `[]` | application/json | `empty` | null |
| Loja headless (sem D-10) | 200 | HTML | text/html | `error` | "HTML instead of JSON" |
| Categoria não encontrada | 404 | any | any | `error` | "HTTP 404" |
| Erro de servidor VTEX | 500 | any | any | `error` | "HTTP 500" |
| Anti-bot / WAF | 403 | any | any | `error` | "HTTP 403" |
| Rate limit VTEX | 429 | any | any | `error` | "HTTP 429" |
| Timeout (rede lenta) | N/A | — | — | `error` | "Timeout" |
| Erro de rede (DNS/TCP) | N/A | — | — | `error` | "Network error: {exc}" |
| JSON inválido (malformed) | 200 | não-parseable | application/json | `error` | "JSON parse error: ..." |
| Marca não-VTEX / sem map. | — | — | — | `no_probe` | null |
| Mapping stale (200+0) | 200 | `[]` | application/json | `empty` | null (URL exposta) |

**Contrato three-state inviolável:** `no_probe` é o quarto estado do relatório, mas NOT um quarto estado de saúde de categoria. É um marcador de cobertura, não de diagnóstico. Na UI, marcas com `no_probe` são renderizadas diferente (sem chip de status por categoria — exibem o marcador D-02).

---

## Validation Architecture

> Nyquist validation está habilitado (workflow.nyquist_validation não é false no config).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | nenhum (usa padrão pytest — .pytest_cache existe) |
| Quick run command | `pytest tests/test_category_diagnostic.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Design: Testes offline/determinísticos (padrão do projeto)

O projeto tem filosofia clara de testes sem rede/WAF (TESTING.md + padrão em `test_vtex_api_client.py` e `test_brand_active.py`):
- `monkeypatch` para substituir funções de I/O
- Objetos fake substituem sessões HTTP (padrão `_FakeSession` / `_FakeResp`)
- `asyncio.run()` para corrotinas (sem `pytest-asyncio` configurado — ou pytest-asyncio 1.3.0 presente mas não obrigatório)
- `BrandManagerService.__new__` + `.brands = {}` para isolar o serviço de arquivo

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DIAG-01 | 200+items → status="ok" | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_ok -x` | ❌ Wave 0 |
| DIAG-01 | 200+empty → status="empty" | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_empty -x` | ❌ Wave 0 |
| DIAG-01 | 404 → status="error", http_status=404 | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_404 -x` | ❌ Wave 0 |
| DIAG-01 | 500 → status="error", http_status=500 | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_500 -x` | ❌ Wave 0 |
| DIAG-01 | 403 → status="error", http_status=403 | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_403 -x` | ❌ Wave 0 |
| DIAG-01 | 429 → status="error", http_status=429 | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_429 -x` | ❌ Wave 0 |
| DIAG-01 | Timeout → status="error", error_detail="Timeout" | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_timeout -x` | ❌ Wave 0 |
| DIAG-01 | HTML body (200) → status="error" | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_html_body -x` | ❌ Wave 0 |
| DIAG-01 | resources header parsed → total_count | unit | `pytest tests/test_category_diagnostic.py::TestClassifier::test_resources_header -x` | ❌ Wave 0 |
| DIAG-01 | engine!="vtex" → no_probe marker | unit | `pytest tests/test_category_diagnostic.py::TestBrandFilter::test_non_vtex_no_probe -x` | ❌ Wave 0 |
| DIAG-02 | GET /diagnostic/brands/{key} retorna 200 | integration (sem rede) | `pytest tests/test_category_diagnostic.py::TestEndpoint -x` | ❌ Wave 0 |

### Estratégia de mock para probe HTTP

O classificador (`classify()`) e o probe (`probe_category()`) devem ser testáveis com o mesmo padrão de `_FakeResp`/`_FakeSession` já estabelecido:

```python
# Padrão do projeto (test_vtex_api_client.py)
class _FakeResp:
    def __init__(self, status, json_data=None, content_type="application/json", headers=None):
        self.status = status
        self._json = json_data
        self.headers = {"Content-Type": content_type, **(headers or {})}

    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False
    async def json(self, content_type=None): return self._json

class _FakeSession:
    def __init__(self, resp): self._resp = resp
    def get(self, url, timeout=None): return self._resp

# Teste de contrato do classificador:
def test_200_with_products_is_ok():
    resp = _FakeResp(200, [{"productId": "1"}], headers={"resources": "0-9/47"})
    session = _FakeSession(resp)
    result = asyncio.run(probe_category(session, "https://marca.vtexcommercestable.com.br", "/roupas/camisas", asyncio.Semaphore(5)))
    assert result["status"] == "ok"
    assert result["total_count"] == 47
    assert result["http_status"] == 200

def test_200_empty_list_is_empty():
    resp = _FakeResp(200, [], headers={"resources": "0-0/0"})
    # ...
    assert result["status"] == "empty"
    assert result["total_count"] == 0

def test_404_is_error():
    resp = _FakeResp(404, None)
    # ...
    assert result["status"] == "error"
    assert result["http_status"] == 404

def test_html_body_is_error():
    resp = _FakeResp(200, None, content_type="text/html; charset=utf-8")
    # ...
    assert result["status"] == "error"
    assert "HTML" in result["error_detail"]

def test_timeout_is_error(monkeypatch):
    # monkeypatch asyncio.TimeoutError na sessão
    # ...
    assert result["status"] == "error"
    assert result["error_detail"] == "Timeout"
```

**Para timeout e network error:** usar `monkeypatch` para fazer `session.get` levantar `asyncio.TimeoutError` ou `aiohttp.ClientError`.

### Sampling Rate

- **Por task commit:** `pytest tests/test_category_diagnostic.py -x -q`
- **Por wave merge:** `pytest tests/ -q`
- **Phase gate:** Suite completa verde antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_category_diagnostic.py` — cobre DIAG-01 (classificador + probe mock) e DIAG-02 (endpoint)
- [ ] Nenhum novo conftest.py necessário — padrão do projeto usa `asyncio.run()` sem fixtures async especiais

*(O restante da infraestrutura de testes — pytest, conftest ausente — já está estabelecido no projeto)*

---

## Security Domain

> security_enforcement não está explicitamente configurado como false — aplicável.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | sim | X-API-Key via `verify_api_key` (já no `api_router`) |
| V3 Session Management | não | Endpoint stateless (GET síncrono, sem sessão de usuário) |
| V4 Access Control | não | Operação de observabilidade (leitura only); sem writes |
| V5 Input Validation | sim | `brand_key` no path: validar contra brand_service (404 se não encontrada) — não passar direto para URL |
| V6 Cryptography | não | Sem criptografia nesta phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via brand_key no endpoint | Tampering | Validar brand_key contra `brand_service.get_brand()` antes de usar; não interpolar diretamente em URLs |
| SSRF via domain do brand_service | Tampering | O `domain` vem de `brand_data.domain` (dado interno confiável, não input do usuário neste endpoint) — risco baixo |
| DoS via "Diagnosticar todas" | DoS | Semáforo global limita concorrência; timeout por probe limita duração |
| Information disclosure via error_detail | Info disclosure | `error_detail` expõe strings de erro internas — aceitável para ferramenta operacional (não exposta a usuário externo) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Detectar categoria vazia via scraping completo | Probe leve 1 GET + header resources | Esta phase | 99% menos I/O por verificação |
| status em português no backend | Enum inglês no contrato API, PT-BR só no display | Esta phase | Neutralidade de idioma na API |

**Deprecated/outdated:**
- Usar `VtexApiClient.validate_url()` (L133-167): faz GET HTML, heurísticas de texto, não adequado para probe de API — substituído pelo probe JSON direto.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_to=9` é o número correto de itens para o probe (retorna até 10 itens como sinal de presença) | Pattern 1 | Se VTEX interpretar `_to=9` diferente de "até o item 9 inclusive" — improvável; L522 do scraper usa `_from=0&_to=chunk_size-1` confirmando este padrão |
| A2 | aiohttp.ClientSession criada no service de diagnóstico (sem reuso de sessão do scraper) é thread-safe para o endpoint síncrono | Pattern 1 | Se houver conflito de event loop com sessões do scraper em execução — baixo risco; FastAPI gerencia event loop corretamente |
| A3 | `DynamicBrand.engine` é "vtex" para todas as 5 marcas VTEX onboardadas na Phase 26 | Pattern 6 + D-02 | Se alguma marca foi cadastrada sem `engine` e ficou com o default "vtex" mas é na prática não-VTEX — improvável dado COMP-02/Phase 25 |

**Se este log está praticamente vazio:** todas as claims críticas foram verificadas diretamente no código-fonte. Sem user confirmation necessária.

---

## Open Questions

1. **`_to` no probe: 0 vs 9**
   - O que sabemos: VTEX usa range `_from=0&_to=N` onde N é o índice (0-based) do último item desejado.
   - O que está em discussão (Claude's Discretion): `_to=0` → 1 item (mínimo para sinal de presença); `_to=9` → 10 itens (mesma chamada que o scraper usa por chunk).
   - Recomendação: Usar `_to=9` — a VTEX processa a mesma query independente do range pedido; o overhead de retornar 10 vs 1 item é negligível, e 10 itens garante que o header `resources` seja populado mesmo em categorias com poucos produtos.

2. **Marcas com `vtex_fq_path` puro (ex: `C:/480/507/`) sem path amigável**
   - O que sabemos: `resolve_category_for_brands` tem um bloco `pass` para esse caso, não gera URL amigável.
   - O que está em discussão: probe usa `?fq=C:/...` ou skip essa categoria.
   - Recomendação: Usar `?fq=` — o endpoint VTEX aceita ambos (confirmado em `search()` L719). Anotar no `probed_url` para o operador ver exatamente o que foi probado.

3. **Semáforo para "Diagnosticar todas": valor exato**
   - O que sabemos: 5 marcas VTEX × ~6 categorias = ~30 probes totais.
   - Recomendação: Semáforo global de 10 para "Diagnosticar todas" (30 probes / 10 = ~3 "rounds" de ~10s cada = ~30s total). Por marca individual, semáforo de 5 (6 probes em ~2 rounds = ~10s).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend | ✓ | 3.14.3 | — |
| aiohttp | Probe HTTP | ✓ | 3.13.3 | — |
| curl_cffi | Auto-discovery (fetch_categories) | ✓ | 0.15.0 | — |
| pytest | Testes | ✓ | 9.0.3 | — |
| pytest-asyncio | Testes async | ✓ | 1.3.0 | asyncio.run() (padrão atual do projeto) |
| Node.js / npm | Frontend | ✓ (inferido — frontend existe) | — | — |

**Missing dependencies with no fallback:** nenhum.

---

## Sources

### Primary (HIGH confidence — verificado diretamente no código-fonte)

- `services/vtex_api_scraper.py` — `fetch_categories` (L46-130), `_request_json` (L228-294), `scrape_category_paged` (L472-675) especialmente header resources (L546-559), `search` fallback full-text (L830-838)
- `services/category_mapping.py` — `resolve_category_for_brands` (L191-250), `_CATEGORY_INDEX`, `_RAW_CATEGORIES`
- `services/brand_service.py` — `list_brands(active_only=False)` (L207), `DynamicBrand` fields
- `services/engines/factory.py` — `get_engine` behavior para engine="unknown" (sem case especial → default VTEXEngine)
- `core/models.py` — `DynamicBrand`, `CategoryMapping`, `BrandSearchResult` como templates Pydantic
- `api/routes_category.py` — padrão de rota fina, `ScrapeMultiBrandRequest`
- `api/__init__.py` — como registrar novo router em `api_router`
- `frontend/src/App.tsx` — `renderTab` (L2107-2117), sidebar nav (L2135-2173), header h1 (L2183-2190), opacity 0.55 (L1705), `MonitoredCategoriesPage` (L1754)
- `frontend/src/api/client.ts` — padrão `ApiClient.request<T>` e métodos estáticos existentes
- `tests/test_vtex_api_client.py` — padrão de `_FakeResp`/`_FakeSession` para mock de HTTP
- `tests/test_brand_active.py` — padrão de `BrandManagerService.__new__` para isolamento de testes

### Secondary (MEDIUM confidence)

- `.planning/codebase/TESTING.md` — filosofia offline/determinística (sem rede/WAF)
- `.planning/REQUIREMENTS.md` — DIAG-01, DIAG-02, Out of Scope
- `.planning/ROADMAP.md` §Phase 29 — success criteria (usa inglês: ok/empty/error)
- `.planning/STATE.md` — decisões acumuladas ([ARCH] is_active chokepoint, padrões de rotas finas)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — tudo verificado no código instalado e no ambiente
- Architecture Patterns: HIGH — derivados diretamente dos padrões existentes no codebase
- Codebase Verification: HIGH — lido e citado com números de linha exatos
- Pitfalls: HIGH — identificados a partir do código real, não de suposições
- Validation Architecture: HIGH — segue o padrão de testes verificado nos testes existentes

**Research date:** 2026-06-22
**Valid until:** 2026-07-22 (codebase estável; sem dependências externas novas)
