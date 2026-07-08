# Phase 39: Cobertura de Marcas — Hugo Boss & Zara - Research

**Pesquisado em:** 2026-06-26
**Domínio:** Mapeamento de categorias VTEX + spike de viabilidade Inditex/Zara
**Confiança geral:** HIGH (Hugo Boss — código já existe e funciona); MEDIUM (Zara — evidência promissora porém não confirmada produto+preço)

---

<user_constraints>
## Restrições do Usuário (de CONTEXT.md)

### Decisões Travadas

- **D-01:** De/para da Hugo Boss vive nos `mappings` dinâmicos do `DynamicBrand` (campo `mappings` em `brands.json`), **não** no bloco hardcoded `_RAW_CATEGORIES` de `category_mapping.py`.
- **D-02:** Mapear apenas os slugs canônicos já existentes (`camisas`, `polos`, `camisetas`, `calcas`, `bermudas`, `jaquetas`, `infantil`) que a Hugo Boss realmente possua no catálogo.
- **D-03:** Paths/`fq` auto-descobertos via `VtexApiClient.fetch_categories("www.hugoboss.com.br")` → `_flatten_vtex_tree` + validados com varredura-amostra antes de gravar.
- **D-04:** De/para curado e persistido estaticamente em `brands.json`; não redescobrir a árvore a cada varredura.
- **D-05 [critério GO Zara]:** GO = ≥3 produtos reais (título + URL `zara.com/br` + preço positivo), com pelo menos uma reexecução bem-sucedida do mesmo fluxo.
- **D-06 [envelope Zara]:** Apenas browser público + `playwright-stealth` (já em `requirements.txt`). Sem proxy pago, CAPTCHA, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado sem aprovação explícita posterior.
- **D-07 [query padrão Zara]:** `camiseta` / `calça`, respeitando o filtro masculino (CAT-01).
- **D-08 [GO Zara]:** Em GO, construir o engine Zara dentro da própria Phase 39.
- **D-09 [NO-GO Zara]:** Em NO-GO, registrar veredito + evidência e deferir COMP-07 ao backlog; não commitar engine incompleto.
- **D-10 [produção pós-GO]:** Código experimental do spike fora de `backend/` até GO; integrar no menor ponto possível (engine + factory) preservando contrato `SearchProductResult`.

### Discrição do Claude (Planner decide)

- Quais categorias da Hugo Boss entram no scheduler de 10 min e a prevenção de falso positivo (restrição: re-execuções de categoria inalterada **não** disparam falso "produto novo").
- Nome/estrutura exata do spike 010, classes e flags.
- Forma exata do `REPORT.md` do spike (exige: veredito GO/NO-GO explícito + evidência reprodutível).
- Local/forma do script de descoberta-e-persistência da Hugo Boss (reusar/estender `backend/scripts/onboard_vtex_brands.py`).
- Número de tentativas no gate da Zara (desde que: baixa frequência + evidência reprodutível).
- Nome do engine Zara em GO.

### Ideias Deferidas (FORA DO ESCOPO)

- Engine Zara/Inditex em fase própria — só alternativa se escopo revelar ser grande demais.
- Frete/checkout/estoque por CEP para Zara/Inditex.
- Proxy residencial/pago/CAPTCHA para Zara.
- Monitoramento Hugo Boss além das categorias mapeadas (fases 44/45).
</user_constraints>

<phase_requirements>
## Requisitos da Phase

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| COMP-06 | Varredura por categoria e monitoramento por categoria da Hugo Boss funcionam (de/para de categorias VTEX, padrão VALID_SLUGS-from-RAW; sem novo engine). | VTEXEngine.discover_categories + auto_match + brands.json `mappings` dinâmicos — toda a infraestrutura existe; gap é apenas popular `mappings: []` da Hugo Boss. |
| COMP-07 | Operador onboarda e busca produtos da Zara (catálogo + preço), gated por spike GO/NO-GO de extração pública. Spike 010 é o deliverable mínimo; engine só em GO. | Spike 008 confirmou zara.com/br acessível via stealth (200 + JSON-LD marker). Spike 010 deve confirmar título + URL + preço para ≥3 produtos. Em NO-GO, COMP-07 deferido com evidência. |
</phase_requirements>

---

## Sumário

Esta phase tem dois blocos independentes com complexidade muito diferente.

**Bloco A — Hugo Boss (COMP-06):** A infraestrutura está completamente pronta. A Hugo Boss (`brand_key="hugoboss"`) já existe em `brands.json` com `engine="vtex"`, `is_active=true` e `mappings: []`. O `category_mapping.py` já faz fallback nos `brand.mappings` dinâmicos (`resolve_category_for_brands` + `get_category_preview`), então popular os `mappings` da Hugo Boss é suficiente para ela aparecer no select de categorias e na varredura VTEX — zero mudança de código de roteamento. O trabalho é: (1) rodar a descoberta da árvore VTEX via `VTEXEngine.discover_categories("hugoboss")`, (2) usar `auto_match` para propor o de/para canônico, (3) validar com varredura-amostra por categoria, (4) persistir em `brands.json`. O `onboard_vtex_brands.py` já implementa exatamente esse pipeline; a fase apenas estende/reutiliza esse script para a Hugo Boss. O scheduler de 10 min (`app.py` → `category_monitor_job`) já roda sobre qualquer entrada em `monitored_categories.json`; a Hugo Boss entra ao criar uma entrada via `POST /monitor/category` com `brand="hugoboss"` e a URL da categoria mapeada.

**Bloco B — Zara (COMP-07):** Trata-se de um spike de viabilidade GO/NO-GO. O spike 008 já provou que `zara.com/br` é acessível via `playwright-stealth` (HTTP 200, 960KB-1.7MB, `jsonld_product_marker` na home). O que falta é confirmar produto+preço **extraíveis programaticamente** para ≥3 produtos reais por uma query de busca pública (`camiseta` / `calça`). O spike 003 testou HTTP direto — 403 — e o spike 008 testou apenas presença do marcador JSON-LD, sem parsear produto completo. O spike 010 deve ir um passo além: navegar até um resultado de busca e extrair título, URL e preço de cada item. Em GO, o engine Inditex é net-new e requer investigação do formato de dados (JSON-LD, endpoint de busca) no próprio spike. Em NO-GO, o trabalho é documentar o bloqueio e deferir o requisito.

**Recomendação principal:** Criar o spike 010 como primeira tarefa da fase (wave 0); o resultado GO/NO-GO determina se o bloco B tem mais 1 task (registrar NO-GO + deferir) ou 3–5 tasks (engine + factory + onboard + smoke). Hugo Boss pode ser planejada e executada em paralelo, sem depender do resultado do spike.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Tier Primário | Tier Secundário | Racional |
|------------|--------------|-----------------|---------|
| Descoberta da árvore de categorias Hugo Boss | API / Backend | — | `VTEXEngine.discover_categories` faz requisição ao endpoint VTEX (`/api/catalog_system/pub/category/tree/`) e acha os paths reais |
| Persistência do de/para Hugo Boss | API / Backend (arquivo) | — | `brand_service.update_mappings` grava em `brands.json`; zero frontend involvement |
| Resolução de categoria na busca/varredura | API / Backend | — | `resolve_category_for_brands` / `category_mapping.py`; já funciona por `brand.mappings` dinâmicos |
| Scheduler de 10 min (Hugo Boss) | API / Backend (APScheduler) | — | `category_monitor_job` já itera `monitored_categories.json`; HB entra via nova entrada no JSON |
| Spike 010 — probe de viabilidade Zara | Spike (fora de `backend/`) | — | Experimento isolado em `.planning/spikes/010-zara-product-price/`; não toca `backend/` até GO |
| Engine Zara (em GO) | API / Backend (`services/engines/`) | EngineFactory | Net-new, mesmo padrão de SFCC/Wake; `factory.py` recebe branch `engine_type == "inditex"` |
| Extração de produto Zara (em GO) | API / Backend | BrowserManager + playwright-stealth | JSON-LD ou endpoint de busca storefront público; sem proxy |

---

## Stack Padrão

### Hugo Boss — nenhum pacote novo

Toda a stack já está em `requirements.txt`. Nenhuma dependência adicional para o bloco A.

| Componente | Versão em uso | Papel |
|------------|--------------|-------|
| `playwright` + `playwright-stealth` | `>=1.40.0` / `>=1.0.6` | BrowserManager (reutilizado em spike 010) |
| `APScheduler` | `>=3.10.0` | Scheduler de 10 min (`app.py`) |
| `pydantic` | `>=2.0` | Modelos (`DynamicBrand`, `CategoryMapping`, `SearchProductResult`) |
| `beautifulsoup4` | `>=4.12.0` | Parsing HTML (reutilizado em spike 010) |
| `fastapi` | `>=0.110.0` | Rotas de categoria e monitor já existentes |

### Zara (spike 010 + engine em GO) — nenhum pacote novo

`playwright-stealth` já é dependência (`requirements.txt`, linha `playwright-stealth>=1.0.6`). O spike 010 pode reutilizá-lo diretamente — mesmo padrão do spike 008.

**Instalação:** nenhuma — tudo já presente.

---

## Auditoria de Legitimidade de Pacotes

Não há pacotes novos a instalar nesta phase. A `playwright-stealth` já está em `requirements.txt` como dependência ativa.

| Pacote | Registro | Idade | Downloads | Repo | slopcheck | Disposição |
|--------|---------|-------|-----------|------|-----------|------------|
| `playwright-stealth` | PyPI | Em uso ativo no projeto | — | github.com/AtuboDad/playwright-stealth | (já verificado em phases anteriores) | Aprovado — já em `requirements.txt` |

**Pacotes removidos por SLOP:** nenhum.
**Pacotes suspeitos:** nenhum.

---

## Padrões de Arquitetura

### Diagrama do Fluxo — Hugo Boss (COMP-06)

```
Script de descoberta (reutiliza onboard_vtex_brands.py)
    │
    ├─► VTEXEngine.discover_categories("hugoboss")
    │       └─► VtexApiClient.fetch_categories("www.hugoboss.com.br")
    │               └─► GET /api/catalog_system/pub/category/tree/3
    │
    ├─► _flatten_vtex_tree(raw_tree)   → lista plana [{name, path}]
    │
    ├─► auto_match(categories)         → proposals [(slug, rel_path, label)]
    │       (filtra feminino/inativo, prefere masculino, dedup por slug)
    │
    ├─► [varredura-amostra por categoria] → confirma produtos reais
    │
    └─► brand_service.update_mappings("hugoboss", mappings)
            └─► brands.json: hugoboss.mappings = [{canonical_slug, vtex_fq_path, label}, ...]

Depois (runtime normal):
  Frontend → GET /canonical-categories
                └─► get_canonical_categories() vê hugoboss.mappings → inclui HB no select
  Operador seleciona categoria → POST /category-preview → resolve_category_for_brands("camisas", ["hugoboss"])
                                              └─► branch dinâmico: usa brand.mappings
  POST /scrape-category-multi → VTEXEngine.run_bulk_scrape(category_url)
  APScheduler (10 min) → category_monitor_job() → run_category_scan(monitor)
```

### Diagrama do Fluxo — Zara (COMP-07)

```
Spike 010 (.planning/spikes/010-zara-product-price/)
    │
    ├─► experiment.py (fora de backend/)
    │       ├─► playwright-stealth: contexto pt-BR, viewport 1366x768, locale, tz
    │       ├─► Probe 1: zara.com/br/pt/search?searchTerm=camiseta&section=MAN
    │       │       └─► parse HTML: JSON-LD?? endpoint de busca JSON??
    │       ├─► Probe 2: extrair ≥3 produtos (título + URL + preço positivo)
    │       ├─► Reexecução: mesmo fluxo → ≥3 produtos estáveis
    │       └─► write_report() → REPORT.md (veredito GO/NO-GO explícito)
    │
    ├─► GO: Phase 39 continua com bloco de engine
    │       ├─► InditexEngine (net-new, em backend/services/engines/)
    │       │       └─► reusa BrowserManager + stealth; parseia JSON-LD / endpoint busca
    │       ├─► factory.py: branch engine_type == "inditex" (lazy import)
    │       ├─► brands.json: adiciona zara (brand_key="zara", engine="inditex", is_active=true)
    │       └─► smoke: busca "camiseta" retorna produtos reais
    │
    └─► NO-GO: registrar veredito + técnicas + assinatura do bloqueio
                deferir COMP-07 ao backlog; zero engine commitado
```

### Estrutura do Projeto para esta Phase

```
backend/
├── data/
│   └── brands.json          # hugoboss.mappings: [] → popular; zara: só em GO
├── scripts/
│   └── onboard_vtex_brands.py  # Reusar/estender: BRAND_TABLE ou script separado
├── services/
│   └── engines/
│       └── inditex_engine.py   # Só em GO; lazy-import em factory.py

.planning/
└── spikes/
    └── 010-zara-product-price/
        ├── experiment.py        # Wave 0 da Zara
        └── REPORT.md            # Gerado pelo experiment.py
```

### Padrão 1: Populando `mappings` dinâmicos via script offline

**O que é:** Rodar `VTEXEngine.discover_categories` + `auto_match` via script (mesmo padrão de `onboard_vtex_brands.py`) e chamar `brand_service.update_mappings("hugoboss", ...)`.

**Quando usar:** Qualquer marca com `engine="vtex"` e `mappings: []`.

**Exemplo (baseado em `onboard_vtex_brands.py` existente):**
```python
# Source: backend/scripts/onboard_vtex_brands.py (padrão estabelecido)
from services.engines.vtex_engine import VTEXEngine
from services.brand_service import brand_service
from core.models import CategoryMapping
from urllib.parse import urlparse

async def discover_hugoboss():
    engine = VTEXEngine("hugoboss")
    raw = await engine.discover_categories()
    for item in raw:
        item["rel_path"] = urlparse(item.get("path") or "").path
    count, proposals = len(raw), auto_match(raw)
    return count, proposals

# proposals = [("camisas", "/masculino/roupas/camisas", "Camisas"), ...]
# persist_mappings(brand_service, "hugoboss", proposals)
```

**Ponto crítico:** `item["path"]` retornado por `_flatten_vtex_tree` é **URL completa** (ex: `https://www.hugoboss.com.br/masculino/roupas/camisas`), não path relativo. O `urlparse(...).path` extrai apenas o path (ex: `/masculino/roupas/camisas`). Esse comportamento está documentado como "Pitfall 3 DEFUSED" em `discover_and_match`. [VERIFIED: código em `backend/scripts/onboard_vtex_brands.py` linha 329]

### Padrão 2: Registrar entrada no scheduler sem falso positivo de "produto novo"

**O que é:** Adicionar a Hugo Boss ao `monitored_categories.json` via `POST /monitor/category`. A lógica de detecção de "produto novo" compara a lista de produtos em `monitored_products_{id}.json` a cada execução do scheduler — se o estado anterior for o mesmo que o novo, não há falso positivo.

**Mecanismo atual:** `run_category_scan` escreve **sempre** o resultado completo da varredura em `monitored_products_{monitor_id}.json` (sobrescreve). O frontend lê esse arquivo para exibir a lista. Não há lógica de diff/alerta automático no `category_monitor_service.py` atual — ele apenas atualiza `last_scraped_at`. O "produto novo" que o critério #2 menciona é identificado a nível de UI/exibição.

**Ação concreta:** Criar a entrada de monitoramento da Hugo Boss (uma por categoria mapeada que se deseje monitorar) via script ou curl, após popular os mappings. Não requer alteração no código do scheduler. [VERIFIED: código em `backend/services/category_monitor_service.py`]

### Padrão 3: Spike de viabilidade GO/NO-GO (padrão spike 008)

**O que é:** Script `experiment.py` isolado em `.planning/spikes/010-zara-product-price/` que usa `sync_playwright` + `Stealth`, navega até a busca da Zara, extrai produtos, avalia o gate e escreve `REPORT.md`.

**Baseado em:** `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` (padrão estabelecido). O spike 010 é mais focado: apenas a Zara, critério GO/NO-GO (D-05).

**URL de busca conhecida do spike 008:** `https://www.zara.com/br/pt/search?searchTerm=polo&section=WOMAN` → 200 OK. Para o spike 010, substituir `polo` por `camiseta` e `section=WOMAN` por `section=MAN` (filtro masculino CAT-01).

**Caminho de extração a investigar no spike:**
1. JSON-LD (`<script type="application/ld+json">`) — spike 008 detectou `jsonld_product_marker` na home; confirmar se a página de busca também retorna JSON-LD com lista de produtos.
2. Endpoint de busca JSON público — inspecionar se a página de busca inicia uma chamada XHR/fetch para um endpoint JSON (ex: `/en/search-results-v3?...` ou similar); se `networkidle` + `wait_for_response` revelarem um endpoint que retorna array de produtos.
3. Parsing de HTML de tiles de produto — fallback se JSON-LD/XHR não estiver disponível; localizar seletores CSS dos cards de produto.

**Landmines conhecidos:**
- HTTP direto → 403 (spike 003). Somente browser (Playwright) funciona.
- `section=WOMAN` na URL do spike 008 — para busca masculina, usar `section=MAN` (ou omitir e filtrar por keywords masculinas).
- Zara BR pode aplicar redirect para `/br/pt/` dependendo do contexto; confirmar URL canônica.
- Anti-bot menos agressivo que Lacoste/Akamai (spike 008 obteve 200 + conteúdo real), mas pode ter detecção de headless via JS. `playwright-stealth` já lida com isso.

### Padrão 4: Integração na `EngineFactory` (em GO)

**O que é:** Adicionar branch `engine_type == "inditex"` em `factory.py` com lazy import, espelhando o padrão da `WakeEngine` / `SFCCEngine`.

```python
# Source: backend/services/engines/factory.py (padrão estabelecido)
if engine_type == "inditex":
    from services.engines.inditex_engine import InditexEngine  # noqa: PLC0415
    return InditexEngine(brand_key)
```

**Contrato obrigatório:** `InditexEngine.search()` deve retornar `BrandSearchResult` com `products: List[SearchProductResult]`. Campos mínimos: `brand`, `product_name`, `url`, `price_full`. `image_url` quando disponível. [VERIFIED: `backend/core/models.py`]

### Anti-Padrões a Evitar

- **Hardcodar paths da Hugo Boss em `_RAW_CATEGORIES`:** viola D-01; o hardcoded é reservado às marcas da casa (aramis/reserva/tommy).
- **Redescobrir árvore VTEX a cada varredura:** viola D-04; causa latência e possível drift gerando falso positivo de "produto novo".
- **Commitar engine Zara antes do GO:** viola D-08/D-09/regra de gate — código incompleto não entra em `backend/`.
- **Usar `section=WOMAN` na query padrão:** viola CAT-01 (filtro masculino); o resultado seria de roupas femininas.
- **Testar Zara com HTTP direto (aiohttp/curl_cffi):** sabidamente 403 desde o spike 003; direto para Playwright stealth.

---

## Não Construir do Zero

| Problema | Não construir | Usar em vez disso | Por quê |
|----------|--------------|-------------------|---------|
| Descoberta da árvore de categorias VTEX | Parser próprio da API VTEX | `VTEXEngine.discover_categories()` + `_flatten_vtex_tree()` | Já implementado, testado, com tratamento de nós malformados |
| Matching slug canônico → path VTEX | Algoritmo próprio de matching | `auto_match()` em `onboard_vtex_brands.py` | Já implementado com lógica de gênero, dedup, preferência masculino, token "mini" vs "feminino" |
| Persistência de mappings | Escrita direta em JSON | `brand_service.update_mappings(brand_key, mappings)` | Dual persistence (dev/prod), idempotente |
| Scheduler de 10 min | Novo job | `category_monitor_job()` + entrada em `monitored_categories.json` | Já roda via APScheduler no `app.py`; HB entra ao criar entrada no JSON |
| Browser stealth para Zara | Novo wrapper Playwright | `BrowserManager.fetch_html()` + `playwright-stealth` | Mesmos args, mesma config de context (locale, tz, viewport, headers), já usado no spike 008 |
| Roteamento de engine na busca | Novo dispatcher | `EngineFactory.get_engine()` + branch `engine_type` | Pattern estabelecido; lazy import evita circular imports |

**Insight principal:** O bloco Hugo Boss é quase inteiramente configuração de dados (`brands.json`), não código. O único código novo é o script de descoberta-e-persistência (que reutiliza funções existentes) e possivelmente um teste de regressão. O código de roteamento (`category_mapping.py`, `routes_category.py`) não precisa ser alterado.

---

## Inventário de Estado em Runtime

> Fase de configuração de dados + spike — aplicável ao bloco de persistência da Hugo Boss.

| Categoria | Itens encontrados | Ação necessária |
|-----------|-----------------|-----------------|
| Dados armazenados | `backend/data/brands.json` — `hugoboss.mappings: []` (vazio); Zara ausente | Código: popular `hugoboss.mappings` via script; adicionar `zara` entry só em GO |
| Dados armazenados | `backend/data/monitored_categories.json` — 1 entrada (aramis/infantil); Hugo Boss ausente | Script/curl: criar entrada(s) de monitoramento HB após mappings populados |
| Config de serviço ativo | APScheduler em `app.py` — `category_monitor_job` a cada 10 min | Nenhuma — scheduler itera `monitored_categories.json` dinamicamente; nova entrada é imediatamente processada no próximo ciclo |
| Estado de OS | Nenhum — scheduler roda em processo Python (não Task Scheduler / cron OS) | Nenhuma |
| Segredos/env vars | Nenhuma variável de ambiente referencia `hugoboss` ou `zara` por nome | Nenhuma |
| Artefatos de build | Nenhum — Python runtime, sem compilação | Nenhuma |

**Nada encontrado em:** OS-registered state (Task Scheduler, pm2, systemd), segredos SOPS com nome da marca.

---

## Armadilhas Comuns

### Armadilha 1: `item["path"]` é URL completa, não path relativo

**O que vai errado:** `VTEXEngine.discover_categories()` retorna `{"name": "...", "path": "https://www.hugoboss.com.br/masculino/..."}`. Se `vtex_fq_path` for salvo como URL completa, `resolve_category_for_brands` constrói `"https://www.hugoboss.com.br" + "https://..."` — URL inválida.

**Por que acontece:** `_flatten_vtex_tree` usa `node.get("url", "")` que retorna a URL completa do nó VTEX.

**Como evitar:** Sempre aplicar `urlparse(item.get("path") or "").path` para extrair o path relativo antes de passar para `auto_match` / `persist_mappings`. Já tratado em `discover_and_match` (linha 329 de `onboard_vtex_brands.py`).

**Sinal de alerta:** `vtex_fq_path` em `brands.json` começa com `"http"` em vez de `"/"`. O `test_vtex_fq_path_is_relative` em `test_vtex_brand_onboarding_contract.py` detecta isso.

### Armadilha 2: `www.hugoboss.com.br` sem `www` não resolve

**O que vai errado:** Passar `"hugoboss.com.br"` (sem `www.`) para `VtexApiClient.fetch_categories` — a requisição falha ou retorna 0 categorias (decisão documentada em STATE.md `[onboarding-live/2026-06-25]`).

**Como evitar:** Usar sempre `"www.hugoboss.com.br"` (com `www.`). O domínio já está correto em `brands.json`. [VERIFIED: `backend/data/brands.json` linha 461]

### Armadilha 3: `section=WOMAN` vs `section=MAN` na busca Zara

**O que vai errado:** URL do spike 008 usa `section=WOMAN` (`zara.com/br/pt/search?searchTerm=polo&section=WOMAN`). Manter esse parâmetro no spike 010 retorna produtos femininos, violando CAT-01.

**Como evitar:** Usar `section=MAN` (ou o equivalente que a Zara aceite para masculino). Verificar no spike se o parâmetro é case-sensitive ou se existe alternativa (ex: `category=SHIRT` ou similar). D-07 especifica respeitando filtro masculino.

### Armadilha 4: Zara — JSON-LD na home ≠ JSON-LD com lista de busca

**O que vai errado:** O spike 008 detectou `jsonld_product_marker` na **home** (`zara.com/br/`), não na página de busca. A página de busca pode retornar JSON-LD diferente (ex: `BreadcrumbList` apenas, sem `ItemList` de produtos) ou nenhum JSON-LD de produto.

**Como evitar:** O spike 010 deve navegar à página de busca (não à home), aguardar o carregamento completo (`networkidle` ou sleep após `domcontentloaded`) e inspecionar **todos** os `<script type="application/ld+json">`. Alternativamente, interceptar requests de rede para localizar endpoint JSON de busca.

### Armadilha 5: Falso positivo de "produto novo" no scheduler

**O que vai errado:** Se o scheduler comparar listas de produtos sem deduplicar por URL/ID, mudanças de ordem ou campos opcionais (ex: `image_url` flactuando) podem gerar falso positivo.

**Como evitar:** O `category_monitor_service.py` atual **sobrescreve** o arquivo de produtos a cada execução — não há lógica de diff automático. O critério #2 do sucesso ("detecta novos produtos sem falso positivo em re-execução de categoria inalterada") é satisfeito porque: (a) re-execução gera o mesmo set de produtos → arquivo idêntico; (b) a exibição ao operador mostra a lista atual sem alarme automático. Confirmar que a UI de monitoramento não dispara notificações baseadas em diferença de contagem ou conteúdo do arquivo.

### Armadilha 6: Activar Zara em `brands.json` antes do GO

**O que vai errado:** Se `zara` for adicionado com `is_active=true` antes do engine estar pronto, qualquer chamada ao scheduler ou busca geral vai tentar instanciar `InditexEngine` e falhar com `NotImplementedError` ou erro de importação — quebra silenciosa.

**Como evitar:** Regra de gate D-08: zero código de engine antes do veredito GO. Se o spike 010 retornar NO-GO, a entrada Zara em `brands.json` não deve ser criada. Em GO, criar a entrada somente após o engine estar integrado e testado (smoke verde).

---

## Exemplos de Código

### Fluxo completo de descoberta da Hugo Boss

```python
# Baseado em: backend/scripts/onboard_vtex_brands.py
import asyncio
from urllib.parse import urlparse
from services.engines.vtex_engine import VTEXEngine
from services.brand_service import brand_service
from scripts.onboard_vtex_brands import auto_match, persist_mappings

async def discover_hugoboss_mappings():
    engine = VTEXEngine("hugoboss")
    raw = await engine.discover_categories()
    # raw = [{"name": "Masculino", "path": "https://www.hugoboss.com.br/masculino"}, ...]
    for item in raw:
        item["rel_path"] = urlparse(item.get("path") or "").path
    count = len(raw)
    proposals = auto_match(raw)
    # proposals = [("camisas", "/masculino/roupas/camisas", "Camisas"), ...]
    return count, proposals

# Após confirmação humana:
# persist_mappings(brand_service, "hugoboss", proposals)
```

### Estrutura do `brands.json` após o script

```json
// backend/data/brands.json — hugoboss após popular mappings
"hugoboss": {
    "brand_key": "hugoboss",
    "brand_name": "Hugo Boss",
    "domain": "www.hugoboss.com.br",
    "engine": "vtex",
    "is_active": true,
    "mappings": [
        {"canonical_slug": "camisas",   "vtex_fq_path": "/masculino/roupas/camisas",   "label": "Camisas"},
        {"canonical_slug": "polos",     "vtex_fq_path": "/masculino/roupas/polos",     "label": "Polos"},
        {"canonical_slug": "camisetas", "vtex_fq_path": "/masculino/roupas/camisetas", "label": "Camisetas"},
        {"canonical_slug": "calcas",    "vtex_fq_path": "/masculino/roupas/calcas",    "label": "Calças"},
        {"canonical_slug": "bermudas",  "vtex_fq_path": "/masculino/roupas/bermudas",  "label": "Bermudas"},
        {"canonical_slug": "jaquetas",  "vtex_fq_path": "/masculino/roupas/jaquetas",  "label": "Jaquetas"},
        {"canonical_slug": "infantil",  "vtex_fq_path": "/kids/menino",                "label": "Menino"}
    ]
}
// Nota: os paths reais são hipotéticos; os verdadeiros são descobertos pelo script via VtexApiClient
```

### Estrutura mínima do `InditexEngine` (em GO)

```python
# backend/services/engines/inditex_engine.py — só em GO
# Baseado no padrão de backend/services/engines/sfcc_engine.py / wake_engine.py
from services.engines.base_engine import BaseEngine
from core.models import BrandSearchResult, SearchProductResult

class InditexEngine(BaseEngine):
    def __init__(self, brand_key: str):
        self.brand_key = brand_key

    def get_engine_name(self) -> str:
        return "Inditex"

    async def search(self, query: str, max_results: int = 10, **kwargs) -> BrandSearchResult:
        from services.brand_service import brand_service
        brand = brand_service.get_brand(self.brand_key)
        if not brand:
            return BrandSearchResult(brand_key=self.brand_key, brand_name=self.brand_key,
                                     error="Marca não encontrada")
        try:
            products = await self._fetch_products(brand.domain, query, max_results)
            return BrandSearchResult(brand_key=self.brand_key, brand_name=brand.brand_name,
                                     products=products, total_found=len(products))
        except Exception as exc:
            return BrandSearchResult(brand_key=self.brand_key, brand_name=brand.brand_name,
                                     error=str(exc))

    async def _fetch_products(self, domain, query, max_results):
        # Implementar baseado no que o spike 010 revelar (JSON-LD ou endpoint JSON)
        raise NotImplementedError("Implementar após spike 010 GO")
```

### Integração na `EngineFactory` (em GO)

```python
# backend/services/engines/factory.py — acrescentar branch APÓS validação GO
# Baseado no padrão estabelecido (linhas 48-57 do factory.py)
if engine_type == "inditex":
    from services.engines.inditex_engine import InditexEngine  # noqa: PLC0415
    return InditexEngine(brand_key)
```

---

## Estado da Arte

| Abordagem antiga | Abordagem atual | Quando mudou | Impacto |
|-----------------|----------------|-------------|---------|
| Hardcodar de/para em `_RAW_CATEGORIES` para toda marca nova | `DynamicBrand.mappings` dinâmicos para marcas concorrentes adicionadas | Phase 26 (COMP-01) | Novas marcas não precisam tocar no código de mapeamento |
| HTTP direto para sites com WAF (requests/curl) | Playwright + playwright-stealth para sites que bloqueiam HTTP headless | Phases 30-32 (SFCC/Wake) | Acesso a sites Inditex/SFCC/etc. requer browser real com fingerprint masking |
| GO/NO-GO sem evidência reprodutível | Spike com `experiment.py` + `REPORT.md` gerado automaticamente | Phase 32 (Wake gate) | Decisão de construir engine baseada em evidência, não em suposição |

**Deprecado/desatualizado:**
- HTTP direto para `zara.com/br`: retorna 403 (spike 003, 2026-06-24). Substituído por Playwright stealth.
- `section=WOMAN` para busca Zara: não adequado para CAT-01 masculino; usar `section=MAN` ou equivalente.

---

## Log de Suposições

| # | Afirmação | Seção | Risco se errado |
|---|-----------|-------|----------------|
| A1 | A Hugo Boss tem categorias VTEX equivalentes a todos os 7 slugs canônicos (camisas, polos, camisetas, calcas, bermudas, jaquetas, infantil). Na prática pode ter menos (ex: sem infantil ou sem polos). | Stack Padrão / Exemplos de Código | Baixo — `auto_match` apenas propõe os slugs encontrados; slugs sem match simplesmente são omitidos do mapeamento (comportamento documentado em `onboard_vtex_brands.py` linha 346). |
| A2 | O parâmetro `section=MAN` (ou equivalente) existe na API de busca pública da Zara BR para filtrar masculino. Baseado em `section=WOMAN` do spike 008, mas `MAN` não foi testado. | Armadilhas / Spike 010 | Médio — se o parâmetro não existir ou tiver nome diferente, os resultados retornarão itens femininos/mistos. O spike 010 deve verificar isso. |
| A3 | A página de busca da Zara contém JSON-LD com lista de produtos (não apenas a home). Spike 008 confirmou `jsonld_product_marker` na home; busca não foi testada com extração de produto. | Armadilhas / Spike 010 | Alto — se JSON-LD não estiver disponível na busca, precisa de parsing HTML ou interceptação de XHR. O spike 010 resolve isso. |
| A4 | Os paths da árvore VTEX da Hugo Boss (`www.hugoboss.com.br`) são acessíveis via `GET /api/catalog_system/pub/category/tree/3` sem autenticação especial (mesmo padrão das demais marcas VTEX). | Padrões / Padrão 1 | Baixo — todas as marcas VTEX do projeto usam este endpoint público sem autenticação. |

---

## Questões em Aberto

1. **Parâmetro de filtro masculino na Zara**
   - O que sabemos: `section=WOMAN` funciona (spike 008). `section=MAN` não foi testado.
   - O que não sabemos: se `section=MAN` existe, ou se o filtro é aplicado de outro jeito (ex: via path `/homem/`, via cookie, via parâmetro `category`).
   - Recomendação: O spike 010 deve testar `section=MAN`; se retornar 0 resultados, tentar sem o parâmetro e filtrar manualmente no parser.

2. **Árvore VTEX da Hugo Boss: profundidade e estrutura**
   - O que sabemos: `www.hugoboss.com.br` funciona como domínio VTEX (busca retorna produtos). `fetch_categories` deve funcionar.
   - O que não sabemos: se a árvore de categorias usa slugs parecidos com os demais (ex: `/masculino/roupas/camisas`) ou estrutura proprietária (ex: `/homens/tops/camisas`). `auto_match` lida bem com variações, mas estruturas muito divergentes podem gerar 0 matches nos primeiros slugs.
   - Recomendação: Wave 0 — rodar o script de descoberta e imprimir a árvore bruta antes de tentar o matching. Planner deve incluir task de inspeção manual da árvore.

3. **Critério de falso positivo no monitor (criterion #2)**
   - O que sabemos: `run_category_scan` sobrescreve o arquivo de produtos a cada execução, sem lógica de diff.
   - O que não sabemos: onde/como a UI determina "produto novo" para exibição. Se há alguma lógica de comparação com o arquivo anterior, uma varredura que retorne campos opcionais diferentes (ex: `available_colors` com ordem diferente) pode gerar divergência.
   - Recomendação: Verificar se o frontend ou o serviço de monitor faz diff entre execuções. Se não há diff, o critério #2 é satisfeito por construção.

---

## Disponibilidade de Ambiente

| Dependência | Exigida por | Disponível | Versão | Fallback |
|-------------|------------|-----------|--------|---------|
| `playwright` | BrowserManager, spike 010 | Deve estar instalado (em `requirements.txt`) | `>=1.40.0` | Sem fallback — necessário para Zara stealth |
| `playwright-stealth` | Spike 010, engine Zara (GO) | Deve estar instalado (`requirements.txt` linha 16) | `>=1.0.6` | Sem fallback — necessário para evasão de detecção headless |
| `APScheduler` | Scheduler de 10 min | Deve estar instalado (`requirements.txt`) | `>=3.10.0` | Sem fallback — mas Hugo Boss entra sem mudar o scheduler |
| Rede pública para `www.hugoboss.com.br` | Script de descoberta | Necessária (acesso ao endpoint VTEX público) | — | Sem fallback; necessária apenas na execução do script de descoberta |
| Rede pública para `www.zara.com/br` | Spike 010 | Necessária | — | Sem fallback para o spike; sem rede = NO-GO por falta de evidência |

**Dependências ausentes sem fallback:** Nenhuma esperada (todas já em `requirements.txt`). Verificar `playwright install` para garantir binários do Chromium.

---

## Arquitetura de Validação

### Framework de Testes

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest (inferido de `backend/tests/test_vtex_brand_onboarding_contract.py` + padrão de tests existentes) |
| Arquivo de config | Nenhum `pytest.ini` encontrado — pytest detecta por convenção |
| Comando rápido | `cd backend && python -m pytest tests/test_vtex_brand_onboarding_contract.py -x -q` |
| Suite completa | `cd backend && python -m pytest tests/ -x -q` |

### Mapeamento Requisito → Teste

| Req ID | Comportamento | Tipo | Comando automatizado | Arquivo existe? |
|--------|--------------|------|---------------------|----------------|
| COMP-06-a | `hugoboss.mappings` populados com slugs válidos do vocabulário canônico | unit | `python -m pytest tests/test_vtex_brand_onboarding_contract.py -x -q` | Existe — testes de contrato cobrem `auto_match` + `update_mappings` + `VALID_SLUGS` |
| COMP-06-b | `resolve_category_for_brands("camisas", ["hugoboss"])` retorna URL válida após mappings populados | unit | `python -m pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_resolve_category_returns_valid_url -x -q` | Existe (adaptado para hugoboss) — Wave 0 |
| COMP-06-c | `get_canonical_categories()` inclui `hugoboss` em `available_brands` para as categorias mapeadas | unit/integration | `python -m pytest tests/test_hugoboss_category_mapping.py -x -q` | Não existe — Wave 0 |
| COMP-06-d | `VTEXEngine.run_bulk_scrape(category_url)` retorna produtos com schema `SearchProductResult` válido para a Hugo Boss | integration (mock) | `python -m pytest tests/test_hugoboss_vtex_scan.py -x -q` | Não existe — Wave 0 |
| COMP-07-spike | `experiment.py` do spike 010 retorna veredito GO/NO-GO com evidência | manual/spike | Execução manual do `experiment.py`; REPORT.md é o artefato | Não existe — Wave 0 |
| COMP-07-engine (GO) | `EngineFactory.get_engine("zara")` retorna `InditexEngine` | unit | `python -m pytest tests/test_inditex_engine.py::TestInditexFactory -x -q` | Não existe — Wave 0 (só em GO) |
| COMP-07-engine (GO) | `InditexEngine.search("camiseta")` retorna ≥1 `SearchProductResult` com `url` em `zara.com/br` e `price_full > 0` (mock) | unit (mock) | `python -m pytest tests/test_inditex_engine.py::TestInditexEngineSearch -x -q` | Não existe — Wave 0 (só em GO) |

### Taxa de Amostragem

- **Por commit de task:** `cd backend && python -m pytest tests/test_vtex_brand_onboarding_contract.py tests/test_hugoboss_category_mapping.py -x -q`
- **Por merge de wave:** `cd backend && python -m pytest tests/ -x -q` (suite completa)
- **Gate da phase:** Suite completa verde antes de `/gsd-verify-work`

### Gaps do Wave 0

- [ ] `backend/tests/test_hugoboss_category_mapping.py` — cobre COMP-06-c (`get_canonical_categories` inclui hugoboss) e COMP-06-b (resolve com brand.mappings dinâmicos de hugoboss)
- [ ] `backend/tests/test_hugoboss_vtex_scan.py` — cobre COMP-06-d (scan retorna `SearchProductResult` válido com mock de `VtexApiClient`)
- [ ] `.planning/spikes/010-zara-product-price/experiment.py` — artefato do spike (não é teste pytest; execução manual)
- [ ] `backend/tests/test_inditex_engine.py` — cobre COMP-07 em GO (factory + search mock); criar SOMENTE após veredito GO

*(Se nenhum gap: "Nenhum — infraestrutura de testes existente cobre todos os requisitos." — não é o caso aqui)*

---

## Domínio de Segurança

> `security_enforcement` não está explicitamente `false` em `.planning/config.json` — incluído.

### Categorias ASVS Aplicáveis

| Categoria ASVS | Aplica | Controle padrão |
|----------------|--------|----------------|
| V2 Autenticação | Não | N/A — sem novo endpoint de autenticação |
| V3 Gerenciamento de sessão | Não | N/A — sessões Playwright são efêmeras e descartadas |
| V4 Controle de acesso | Parcialmente | Rotas existentes já protegidas por `X-API-Key` via `verify_api_key`; novas rotas (se houver) devem herdar o mesmo padrão |
| V5 Validação de entrada | Sim | `CategoryMapping` (Pydantic) valida `canonical_slug`, `vtex_fq_path`, `label`; `DynamicBrand` valida `domain` (limpeza de esquema em `clean_domain`) |
| V6 Criptografia | Não | Sem novos segredos ou dados criptografados nesta phase |

### Padrões de Ameaça Conhecidos

| Padrão | STRIDE | Mitigação padrão |
|--------|--------|-----------------|
| Path traversal via `vtex_fq_path` | Tampering | `vtex_fq_path` deve começar com `/`; validado em `persist_mappings` (filtra paths que não começem com `/`) e em `test_vtex_fq_path_is_relative` |
| URL de categoria forjada via `custom_url` em `ScrapeCategoryRequest` | Tampering | `clean_url()` já corrige duplicação de esquema; `brand_service.get_brand()` valida que a marca existe; rotas protegidas por `X-API-Key` |
| Dados de produto externos (Zara/VTEX) sem sanitização | Information Disclosure | `SearchProductResult` via Pydantic; campos `price_full` validados como `float > 0`; `url` não é executada, apenas armazenada/exibida |
| Spike 010 vazando credenciais/estado para `backend/` | Tampering | Regra D-08: código do spike fica exclusivamente em `.planning/spikes/010-*/`; `experiment.py` não importa de `backend/` como efeito colateral — apenas importa helpers de parsing quando necessário |

---

## Fontes

### Primárias (confiança HIGH)

- `backend/services/engines/vtex_engine.py` — `discover_categories`, `_flatten_vtex_tree` (verificado diretamente)
- `backend/services/category_mapping.py` — `resolve_category_for_brands`, `get_category_preview`, lógica de fallback dinâmico (verificado diretamente)
- `backend/scripts/onboard_vtex_brands.py` — `auto_match`, `discover_and_match`, `persist_mappings`, `onboard_brand` (verificado diretamente)
- `backend/data/brands.json` — estado atual da Hugo Boss: `engine="vtex"`, `mappings: []` (verificado diretamente)
- `backend/services/category_monitor_service.py` — `run_category_scan`, `category_monitor_job` (verificado diretamente)
- `backend/app.py` — `scheduler.add_job(category_monitor_job, "interval", minutes=10)` (verificado diretamente)
- `backend/services/engines/factory.py` — padrão lazy import para engines (verificado diretamente)
- `backend/core/models.py` — `SearchProductResult`, `BrandSearchResult`, `DynamicBrand`, `CategoryMapping` (verificado diretamente)
- `.planning/spikes/008-lacoste-antibot-zara-recheck/REPORT.md` — zara.com/br 200 + `jsonld_product_marker` via stealth (verificado diretamente)
- `.planning/spikes/003-sfcc-inditex-storefront-mvp/REPORT.md` — HTTP direto Zara BR = 403 (verificado diretamente)
- `.planning/spikes/008-lacoste-antibot-zara-recheck/experiment.py` — padrão de spike: ProbeResult, Stealth, write_report (verificado diretamente)

### Secundárias (confiança MEDIUM)

- STATE.md `[onboarding-live/2026-06-25]` — Hugo Boss confirmada como VTEX ativa, `www.hugoboss.com.br` (com www obrigatório)
- CONTEXT.md 39 — decisões D-01..D-10 (documento de contexto autoritativo desta phase)
- REQUIREMENTS.md — COMP-06, COMP-07 (escopo formal)

---

## Metadados

**Breakdown de confiança:**

| Área | Nível | Razão |
|------|-------|-------|
| Stack Hugo Boss | HIGH | Código verificado diretamente; Hugo Boss já ativa como VTEX; pipeline de onboarding testado em 5 outras marcas |
| Arquitetura Hugo Boss | HIGH | Fluxo idêntico ao das demais marcas VTEX dinâmicas já em produção |
| Stack Zara (spike 010) | MEDIUM | `playwright-stealth` verificado em `requirements.txt`; URL de busca e parâmetros de produto não confirmados (A2, A3) |
| Arquitetura Zara (GO) | MEDIUM | Padrão de integração na `EngineFactory` verificado; formato de dados do InditexEngine depende do resultado do spike |
| Armadilhas | HIGH | Todas derivadas de código verificado ou de spikes documentados anteriores |

**Data da pesquisa:** 2026-06-26
**Válido até:** ~2026-07-26 (stable — VTEX API pública estável; Zara anti-bot pode mudar)
