# Phase 40: Onboarding por URL & Workflows de Adição ao Monitoramento - Research

**Researched:** 2026-06-29
**Domain:** FastAPI backend (Python) + React/TS frontend; JSON-file persistence; codebase-grounded
**Confidence:** HIGH (all findings verified against actual source files)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 [inferência de nome]:** Inferir o nome da marca por ordem de precedência JSON-LD/OG (`brand`/`organization`/`og:site_name`) → `<title>` → domínio (ex.: `hugoboss.com.br` → "Hugo Boss"). Reaproveitar a resposta do fetch da home que o `detect_engine` já faz — sem request HTTP extra. O campo de nome é sempre editável no formulário de confirmação.
- **D-02 [fluxo identify vs salvar — dois endpoints]:** Criar `POST /brands/identify` como dry-run: detecta engine + infere nome + normaliza domínio e NÃO persiste. A UI mostra o formulário pré-preenchido; o operador confirma/edita; o `POST /brands/` existente salva. Separação limpa — `create_brand` permanece o ponto único de escrita, intacto.
- **D-03 [engine='unknown' no identify]:** Quando o identify detecta `engine='unknown'`, avisar e permitir override manual do engine, ou salvar mesmo assim. Não travar o cadastro.
- **D-04 [alvo = price_monitor]:** "Adicionar ao monitoramento" tem como alvo o monitor de preços (`POST /monitor/start` em `routes_product.py`), passando `url` + `brand` do card. Não é o monitor de categoria (`routes_monitor.py /category`).
- **D-05 [parâmetros = defaults fixos, 1 clique]:** Clique único adiciona com `interval`/`duration` padrão, sem modal. Operador ajusta depois na aba de monitores.
- **D-06 [semântica de duração persistente]:** Monitorar preço de concorrente é acompanhamento contínuo — o monitor não deve expirar sozinho cedo. Usar duração longa ou tratar `0`/`None` como indefinido.
- **D-07 [botão nas três superfícies]:** Botão "Adicionar ao monitoramento" aparece de forma consistente nas três superfícies (busca comparativa, busca por SKU, monitor de categoria), todas chamando o mesmo endpoint/fluxo idempotente.
- **D-08 [normalização de URL — conservadora]:** Normalizar: host em lowercase, remover `www`, forçar `https`, remover trailing slash, descartar apenas params de tracking conhecidos (`utm_*`, `gclid`, `fbclid`). Manter o resto do path+query.
- **D-09 [comportamento idempotente com feedback]:** Se já monitorado e ativo → toast "já está em monitoramento" (no-op). Se existe mas está parado → reativa o monitor existente.
- **D-10 [persistência — promover a brands reais + reusar is_active]:** Promover Mercado Livre / Netshoes / Amazon a entradas reais em `brands.json` com `is_active`, toggladas pelo `PATCH /brands/{brand_key}/active` existente. Remover a injeção em runtime do `list_brands()` (`routes_brands.py:133-160`).
- **D-11 [enforcement — por request]:** O `cross_marketplace_service` monta `self.engines` a cada `cross_marketplace_search`, lendo o estado ativo na hora e incluindo só os marketplaces ativos.

### Claude's Discretion
- UI/UX exata: aparência e posição dos toggles na tela de configurações; estilo do formulário de confirmação do onboarding; rótulo/ícone do botão "Adicionar ao monitoramento" — mantendo consistência visual com o app.
- Valores numéricos exatos dos defaults de `interval`/`duration` (D-05/D-06) e a representação concreta de "indefinido" em `PriceMonitorConfig`.
- Forma exata da normalização de URL (D-08) — função utilitária reusável; lista exata de tracking params a descartar.
- Se marketplaces desativados continuam visíveis (cinza) nos filtros de busca ou somem — desde que o `cross_marketplace_service` os exclua de fato.
- Estrutura do `brand_key` dos marketplaces promovidos (D-10) — preservar os keys atuais (`mercado_livre`, `netshoes`, `amazon`).

### Deferred Ideas (OUT OF SCOPE)
None — discussão ficou dentro do escopo da phase (3 success criteria do roadmap).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UX-03 | Operador cadastra uma marca colando apenas a URL; o sistema detecta marca + engine (`detect_engine` + inferência de nome) e apresenta para confirmação antes de salvar, com override manual disponível. | `POST /brands/identify` dry-run reusa `detect_engine` + BeautifulSoup name inference. |
| UX-04 | Operador adiciona um produto ao monitoramento direto da busca comparativa, da busca por SKU e do monitor de categoria; criação idempotente (dedup por url+marca). | Botão por card → `POST /monitor/start` com dedup hook em `start_monitor`. |
| UX-05 | Toggles de ativar/desativar disponíveis também para os marketplaces virtuais (Mercado Livre, Netshoes, Amazon), respeitados pelo `cross_marketplace_service`. | Promover marketplaces a `brands.json`; remover injeção runtime; rebuild `self.engines` por request. |
</phase_requirements>

---

## Summary

Esta phase é quase inteiramente codebase-grounded. As três entregas (onboarding por URL, botão "adicionar ao monitoramento" e toggles de marketplace) reutilizam infraestrutura existente: `detect_engine`, `create_brand`, `PATCH /brands/{key}/active`, `POST /monitor/start`, e o chokepoint `list_brands(active_only=True)`. Nenhum novo pacote externo é necessário — `beautifulsoup4` já é dependência instalada e é a ferramenta correta para a inferência de nome.

A mudança mais cirúrgica e de maior risco arquitetural é a D-11 (rebuild de `self.engines` por request no `CrossMarketplaceService`): atualmente `self.engines` é um dict fixo inicializado no `__init__`, e a troca para leitura dinâmica precisa ser feita sem introduzir overhead nas buscas normais. A D-09 (dedup idempotente de monitor) requer um scanner linear sobre `monitor_service.monitors` antes de cada `start_monitor` — simples mas ausente hoje.

**Primary recommendation:** Implementar em waves: (1) backend `POST /brands/identify` + normalização de URL + dedup de monitor + promoção de marketplaces a `brands.json` + rebuild por request no cross_marketplace; (2) frontend botão nas três superfícies + formulário de onboarding + exposição dos toggles de marketplace.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Detecção de engine + inferência de nome | API Backend | — | `detect_engine` já vive em `routes_brands.py`; inferência de nome é parsing de HTML server-side |
| Dry-run identify (não persiste) | API Backend | — | Backend evita persistência acidental; frontend recebe apenas resultado |
| Persistência de marca (confirmação) | API Backend | — | `create_brand` é o único ponto de escrita; permanece intacto |
| Normalização de URL para dedup | API Backend | — | Lógica pura Python; reutilizável por `start_monitor` e `POST /brands/identify` |
| Dedup de monitor | API Backend | — | `monitor_service.monitors` vive no processo servidor; scanner deve rodar server-side |
| Botão "Adicionar ao monitoramento" | Frontend | — | UI action que chama `POST /monitor/start`; feedback toast no cliente |
| Formulário de confirmação de onboarding | Frontend | — | Form pré-preenchido a partir da resposta do `/brands/identify` |
| Toggles de marketplace | Frontend (UI) + Backend (enforcement) | — | Toggle de UI chama `PATCH /brands/{key}/active`; enforcement no `cross_marketplace_service` |
| Enforcement de marketplace ativo/inativo | API Backend | — | `CrossMarketplaceService._fetch_all_engines` lê `brand_service.list_brands(active_only=True)` por request |

---

## Standard Stack

### Core (todos já instalados — sem novos pacotes)

| Library | Installed Version | Purpose | Verification |
|---------|------------------|---------|--------------|
| `beautifulsoup4` | `>=4.12.0` (requirements.txt l.12) | Parsing de HTML para inferência de nome (JSON-LD, OG, `<title>`) | [VERIFIED: requirements.txt] |
| `aiohttp` | `>=3.9.0` (requirements.txt l.8) | Fetch da home page já feito por `detect_engine` | [VERIFIED: requirements.txt] |
| `fastapi` | `>=0.110.0` | Novo endpoint `POST /brands/identify` | [VERIFIED: requirements.txt] |
| `urllib.parse` | stdlib Python | Normalização de URL (D-08) — zero-dep | [VERIFIED: stdlib] |

**Nenhum novo pacote a instalar.** Todos os building blocks já existem.

---

## Package Legitimacy Audit

> Nenhum novo pacote externo é instalado nesta phase. Todos os artefatos reutilizam dependências já presentes em `backend/requirements.txt`.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Operador cola URL
        |
        v
POST /brands/identify (dry-run)
  |- detect_engine(domain)  ← reutiliza fetch da home (Step 3 aiohttp)
  |      |
  |      v  [html já disponível como str]
  |- infer_brand_name(html, domain)  ← BeautifulSoup: JSON-LD → OG → <title> → domínio
  |- normalize_domain(url)  ← urllib.parse
  |
  v
Resposta: { engine, inferred_name, domain }  (sem persistir)
        |
        v
Frontend mostra formulário pré-preenchido
(campos editáveis: nome, engine, domain)
        |
        v  [operador confirma/edita]
POST /brands/  (create_brand — ponto único de escrita, intacto)
        |
        v
brands.json atualizado



Busca retorna produtos  →  card tem botão "Adicionar ao monitoramento"
        |
        v
Frontend: ApiClient.addToMonitor({ url, brand })
        |
        v
POST /monitor/start
  |- normalize_url(url)  → dedup scan de monitor_service.monitors
  |    |- encontrou ativo? → 409 / toast "já monitorado"
  |    |- encontrou inativo? → resume_monitor()
  |    |- não encontrou? → cria novo monitor (uuid job_id)
  v
price_monitors.json atualizado



Marketplaces em brands.json com is_active
        |
        v  [PATCH /brands/{key}/active toggle]
brand_service.set_active(key, is_active)  →  brands.json

        |  [cross_marketplace_search chamada]
        v
CrossMarketplaceService.cross_marketplace_search()
  |- engines = _build_engines_from_active_brands()   ← NEW, por request
  |      (lê brand_service.list_brands(active_only=True))
  |      (filtra keys: mercado_livre, netshoes, amazon)
  |- asyncio.gather(*(fetch(n, e) for n, e in engines.items()))
```

### Recommended Project Structure

Nenhuma nova pasta. Alterações cirúrgicas em arquivos existentes:

```
backend/
├── api/
│   └── routes_brands.py        # novo POST /brands/identify; remover injeção runtime l.133-160
├── services/
│   ├── cross_marketplace_service.py  # rebuild engines por request (D-11)
│   ├── price_monitor_service.py      # dedup hook em start_monitor (D-09)
│   └── url_utils.py                  # NOVO: normalize_url() — stdlib urllib.parse
├── data/
│   └── brands.json             # promover mercado_livre, netshoes, amazon como entradas reais
frontend/src/
├── api/
│   └── client.ts               # novo identifyBrand(), addToMonitor() helper
└── App.tsx                     # botão por card nas 3 superfícies + formulário de onboarding
                                # + exibir toggles de marketplace em SettingsPage
```

### Pattern 1: detect_engine refatorado para retornar HTML junto com engine

**What:** Para o `POST /brands/identify` não fazer um segundo request HTTP, `detect_engine` precisa expor o HTML da home que já busca internamente (Step 3). A forma mais limpa é refatorar `detect_engine` para retornar uma tupla `(engine: str, home_html: str | None)` — o HTML é `None` se o Step 3 não chegou a executar (Shopify via collections.json ou VTEX via API pura).

**When to use:** Apenas no `POST /brands/identify`. O `create_brand` continua chamando `detect_engine` e descartando o HTML (mantém a assinatura atual com alias ou unpacking).

```python
# Source: [VERIFIED: routes_brands.py l.14-100 — análise direta]
async def detect_engine(domain: str) -> tuple[str, str | None]:
    """Retorna (engine, home_html_ou_None)."""
    # Steps 1 e 2: Shopify via collections.json, VTEX via API → retornam cedo sem HTML
    ...
    # Step 3: HTML da home — agora capturado para reutilização
    try:
        async with session.get(base_url, ...) as resp:
            html = await resp.text()
            html_lower = html.lower()
            if "fbitsstatic.net" in html_lower:
                return "wake", html
            if "vtexassets.com" in html_lower or "vtexcommercestable.com" in html_lower:
                return "vtex", html
            if "cdn.shopify.com" in html_lower or "window.shopify" in html_lower:
                return "shopify", html
            if "static.zara.net" in html_lower or ...:
                return "zara", html
            # Nenhum match mas temos o HTML — retorna para inferência de nome
            return _sfcc_or_unknown(domain, rendered_html=None), html
    except Exception:
        pass
    # Step 6: SFCC via Playwright
    try:
        rendered_html = await BrowserManager.fetch_html(...)
        if "demandware.static" in rendered_html.lower():
            return "sfcc", rendered_html
    except Exception:
        pass
    return "unknown", None
```

**Atenção:** callers existentes (`create_brand`) usam `engine = await detect_engine(domain)`. Após a refatoração retornar uma tupla, todos os callers existentes precisam ser atualizados para `engine, _ = await detect_engine(domain)`. Há apenas um caller hoje (`create_brand`).

### Pattern 2: Inferência de nome da marca via BeautifulSoup

**What:** Ordem de precedência D-01: JSON-LD → Open Graph → `<title>` → domínio.

```python
# Source: [VERIFIED: zara_parser.py — padrão JSON-LD existente; beautifulsoup4 já instalado]
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import json as _json

def infer_brand_name(html: str | None, domain: str) -> str:
    """Infere nome da marca. Fallback: deriva do domínio."""
    if html:
        soup = BeautifulSoup(html, "html.parser")

        # 1. JSON-LD: procura Organization.name ou Brand.name
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = _json.loads(tag.string or "")
                # Normaliza lista ou objeto único
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") in ("Organization", "Brand"):
                        name = item.get("name", "").strip()
                        if name:
                            return name
            except Exception:
                pass

        # 2. Open Graph: og:site_name
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content", "").strip():
            return og["content"].strip()

        # 3. <title>: pega a primeira parte antes de " - " ou " | "
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            for sep in (" - ", " | ", " – ", " — "):
                if sep in title:
                    title = title.split(sep)[0].strip()
                    break
            if title:
                return title

    # 4. Fallback: deriva do domínio (ex: hugoboss.com.br → "Hugo Boss")
    host = domain.lower().replace("www.", "").split(".")[0]
    # Insere espaço antes de maiúsculas em camelCase: hugoboss → Hugo Boss
    name = re.sub(r"([a-z])([A-Z])", r"\1 \2", host)
    # Capitaliza cada palavra
    return " ".join(w.capitalize() for w in name.replace("-", " ").replace("_", " ").split())
```

### Pattern 3: Normalização conservadora de URL para dedup (D-08)

**What:** stdlib `urllib.parse` — zero dependências extras.

```python
# Source: [VERIFIED: stdlib urllib.parse — análise direta]
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse

_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "gclid", "fbclid", "msclkid", "dclid",
})

def normalize_url(url: str) -> str:
    """
    Normalização conservadora para dedup de monitor (D-08).
    - lowercase host, strip www, força https, strip trailing slash
    - descarta apenas tracking params conhecidos; mantém path+query restantes
    """
    parsed = urlparse(url.strip())
    scheme = "https"
    host = parsed.netloc.lower().lstrip("www.")  # remove www. prefixo
    if not host:
        return url  # URL malformada — devolve sem alterar
    path = parsed.path.rstrip("/") or "/"
    # Filtra tracking params, preserva ordem dos demais
    filtered_qs = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in _TRACKING_PARAMS
        and not k.lower().startswith("utm_")
    ]
    query = urlencode(filtered_qs)
    return urlunparse((scheme, host, path, "", query, ""))
```

### Pattern 4: Dedup idempotente em start_monitor (D-09)

**What:** Antes de criar novo job, scanner linear sobre `monitor_service.monitors` comparando `normalize_url(url)` + `brand`.

```python
# Source: [VERIFIED: price_monitor_service.py l.51-66 — análise direta]
async def start_monitor(self, job_id: str, url: str, brand: str, interval: int, duration: int):
    norm_url = normalize_url(url)
    # Dedup scan — O(n) sobre monitores existentes (quantidade tipicamente < 100)
    for existing_id, config in self.monitors.items():
        if normalize_url(config.url) == norm_url and config.brand.lower() == brand.lower():
            if config.active:
                # Retorna sinal especial para o caller saber que já está ativo
                return config, "already_active"
            else:
                # Reativa o monitor existente em vez de criar um novo
                await self.resume_monitor(existing_id)
                return self.monitors[existing_id], "reactivated"
    # Novo monitor
    config = PriceMonitorConfig(
        job_id=job_id,
        url=url,
        brand=brand,
        interval_minutes=interval,
        duration_hours=duration,
        active=True
    )
    ...
```

O `POST /monitor/start` em `routes_product.py` trata o retorno e responde com HTTP 200 + `status: "already_active"` ou `status: "reactivated"` conforme o caso. O frontend interpreta o campo `status` para exibir o toast correto.

### Pattern 5: duration_hours — campo armazenado mas não enforced (D-06)

**What:** Análise do `_monitor_loop` confirma que `duration_hours` é armazenado em `PriceMonitorConfig` mas **nunca verificado** no loop: o único critério de parada é `config.active`. O loop roda enquanto `active is True` indefinidamente. Não há lógica de `timedelta` ou expiração por horas.

**Consequência para o planner:** `duration_hours=0` (ou qualquer valor) funciona como "indefinido" de fato — o campo existe no modelo mas não drive nenhum comportamento de expiração. O default de D-05 pode usar qualquer valor inteiro; recomenda-se `duration_hours=87600` (10 anos em horas) para sinalizar clareza semântica, ou simplesmente manter `24` sabendo que o campo é inerte.

**Recomendação:** Não alterar a semântica de `duration_hours` nesta phase — o comportamento já é indefinido por design acidental. O default de 1 clique (D-05) pode usar `interval=10` (minutos), `duration=24` (horas — inerte).

### Pattern 6: Promover marketplaces a brands.json (D-10)

**What:** Entradas a inserir em `brands.json` com `is_active: true` inicialmente. Os `brand_key` atuais preservados.

```json
// Source: [VERIFIED: brands.json + cross_marketplace_service.py __init__ l.154-157]
"mercado_livre": {
  "brand_key": "mercado_livre",
  "brand_name": "Mercado Livre",
  "domain": "mercadolivre.com.br",
  "engine": "mercadolivre",
  "review_provider": "none",
  "review_store_id": null,
  "vtex_account": null,
  "logo_url": null,
  "wake_access_token": null,
  "search_url_template": null,
  "proxy_url": null,
  "mappings": [],
  "is_active": true
}
// Repetir para "netshoes" (engine="netshoes") e "amazon" (engine="amazon")
```

Após inserção: remover o bloco de injeção runtime em `routes_brands.py` linhas 133–160. `list_brands()` passa a retornar os marketplaces de `brands.json` naturalmente.

### Pattern 7: Rebuild de self.engines por request (D-11)

**What:** Mover a construção do dict `engines` do `__init__` para `_fetch_all_engines`, lendo `brand_service.list_brands(active_only=True)` a cada chamada.

```python
# Source: [VERIFIED: cross_marketplace_service.py l.152-158 + l.285-346]
# ANTES (hardcoded no __init__):
class CrossMarketplaceService:
    def __init__(self):
        self.engines = {
            "Mercado Livre": MercadoLivreEngine(),
            "Netshoes": NetshoesEngine(),
            "Amazon": AmazonEngine(),
        }

# DEPOIS (por request, lê brand_service):
_ENGINE_MAP = {
    "mercadolivre": ("Mercado Livre", MercadoLivreEngine),
    "netshoes":     ("Netshoes",      NetshoesEngine),
    "amazon":       ("Amazon",        AmazonEngine),
}

class CrossMarketplaceService:
    def __init__(self):
        # Instâncias reutilizáveis (stateless) — criadas uma vez, selecionadas por request
        self._engine_instances = {
            key: cls() for key, (_, cls) in _ENGINE_MAP.items()
        }

    def _active_engines(self) -> dict:
        """Retorna {display_name: engine_instance} apenas para marketplaces ativos."""
        active_brands = brand_service.list_brands(active_only=True)
        active_keys = {b.brand_key for b in active_brands}
        result = {}
        for engine_key, (display_name, _) in _ENGINE_MAP.items():
            if engine_key in active_keys:
                result[display_name] = self._engine_instances[engine_key]
        return result
```

`_fetch_all_engines` substitui `self.engines.items()` por `self._active_engines().items()`. As instâncias de engine permanecem singletons (stateless entre requests); apenas o dict de participantes é construído por chamada — custo O(n) trivial.

**Importante:** `_enrich_pdp_and_shipping` usa `p["plataforma"]` para fazer `self.engines[plat]`. Após a refatoração, esse lookup precisa usar `self._engine_instances` pelo key de engine ou manter um mapeamento display_name → instance separado. Recomenda-se manter um `self._by_display: dict` persistente apontando para as instâncias por display_name.

### Pattern 8: Frontend — botão "Adicionar ao monitoramento" por card

**What:** O botão aparece nas três superfícies. O padrão de `e.preventDefault() + e.stopPropagation()` já está documentado no código de frete (linhas 1581-1583) — o mesmo deve ser usado aqui pois os cards são `<a href>`.

```typescript
// Source: [VERIFIED: App.tsx l.1524-1531 — card é <a> href]
// Botão dentro do product-card (que é um <a>):
<button
  type="button"
  className="btn-icon btn-sm"
  title="Adicionar ao monitoramento"
  onClick={async (e) => {
    e.preventDefault();
    e.stopPropagation();
    await handleAddToMonitor(p.url, brandKey);
  }}
>
  <Plus size={14} />
</button>
```

`handleAddToMonitor` chama `ApiClient.startMonitor({ url, brand: brandKey, interval: 10, duration: 24 })` e interpreta `response.status` para exibir o toast correto via `toast.success` / `toast.info`.

### Anti-Patterns to Avoid

- **Não reutilizar o endpoint `POST /brands/` como identify:** D-02 exige dry-run separado; chamar `create_brand` e depois "desfazer" seria frágil e quebraria o log de marcas.
- **Não chamar `detect_engine` duas vezes (uma no identify, outra no save):** Uma segunda chamada pode retornar resultado diferente se o site estiver instável. O frontend deve repassar o `engine` inferido do identify como campo do formulário de confirmação.
- **Não criar segundo mecanismo de "marketplace ativo":** D-10 exige reutilização do `PATCH /brands/{key}/active` existente. Qualquer flag paralela quebraria a consistência.
- **Não usar `self.engines.items()` no `__init__` do CrossMarketplaceService:** O dict hardcoded ignora o estado `is_active` — ponto de falha central do success criterion 3.
- **Não usar `utm_` como prefixo isolado em set de exclusão:** `utm_source` etc. são params compostos. O set deve conter os nomes completos E a cláusula `startswith("utm_")` para pegar variantes futuras.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parse de HTML para metadados | Parser manual com regex | `BeautifulSoup(html, "html.parser")` — já instalado | Regex em HTML é frágil: namespaces, encoding, whitespace |
| Parse de JSON-LD | Regex no script tag | `json.loads(tag.string)` via bs4 | JSON-LD pode ter caracteres escapados e whitespace |
| Normalização de URL | String split/replace manual | `urllib.parse` (stdlib) | Cuida de encoding, query string ordering, fragmentos |
| Toggle de marca | Novo endpoint ou tabela | `PATCH /brands/{key}/active` + `brand_service.set_active` | Chokepoint único já testado; criar paralelo quebraria MGMT-01 |
| Dedup de URL | Comparação de string pura | `normalize_url()` + comparação de strings normalizadas | URLs com tracking params idênticos falhariam dedup simples |

---

## Common Pitfalls

### Pitfall 1: detect_engine retorna cedo sem HTML para Shopify/VTEX (Steps 1 e 2)
**What goes wrong:** Steps 1 (Shopify via `/collections.json`) e 2 (VTEX via `/api/catalog_system/`) retornam cedo sem passar pelo Step 3 que busca o HTML. O `infer_brand_name` recebe `html=None` e precisa cair no fallback de domínio.
**Why it happens:** `detect_engine` tem return antecipado antes do fetch do HTML da home.
**How to avoid:** `infer_brand_name(html=None, domain=...)` cai diretamente na lógica de derivação do domínio. Testar esse caminho explicitamente.
**Warning signs:** Nome inferido para Shopify/VTEX sempre vira o fallback de domínio.

### Pitfall 2: `VIRTUAL` guard em SettingsPage (App.tsx l.2325) bloqueia toggle
**What goes wrong:** `const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon']` faz `canToggle = !VIRTUAL.includes(b.brand_key)` — os toggles ficam desabilitados mesmo após promover os marketplaces a `brands.json`.
**Why it happens:** A guarda foi criada no MGMT-02 justamente para proteger contra o PATCH 404 que existia quando os marketplaces eram injetados em runtime sem registro no backend.
**How to avoid:** Remover o array `VIRTUAL` e a guarda `canToggle` em `SettingsPage` nesta phase — após a promoção a `brands.json`, o PATCH passa a funcionar para `mercado_livre`/`netshoes`/`amazon`.

### Pitfall 3: CategoryPage filtra marketplaces hardcoded (App.tsx l.531)
**What goes wrong:** `brands.filter(b => !['mercado_livre', 'netshoes', 'amazon'].includes(b.brand_key?.toLowerCase()))` na `CategoryPage` remove os marketplaces do seletor de categorias. Isso é CORRETO e deve ser preservado — marketplaces não têm varredura por categoria.
**Why it happens:** Filtro intencional do MGMT-02.
**How to avoid:** Manter esse filtro em `CategoryPage`. Remover somente o `VIRTUAL` guard em `SettingsPage` (ver Pitfall 2). Os dois são distintos.

### Pitfall 4: BannersPage tem seu próprio filtro de marketplaces (App.tsx l.886)
**What goes wrong:** `const virtualMarketplaces = new Set(['mercado_livre', 'netshoes', 'amazon'])` em `BannersPage` filtra marketplaces da lista de marcas ativas para banners. Também é correto e deve ser preservado.
**How to avoid:** Manter o filtro em `BannersPage`. Revisar CADA uso do hardcoded `VIRTUAL` e decidir qual remover (SettingsPage) vs. manter (CategoryPage, BannersPage).

### Pitfall 5: _enrich_pdp_and_shipping usa self.engines[plat] diretamente
**What goes wrong:** Após refatorar para `_active_engines()`, o método `_enrich_pdp_and_shipping` ainda referencia `self.engines` (l.456: `if plat in self.engines`). Se `self.engines` deixar de existir, quebra com `AttributeError`.
**Why it happens:** `_enrich_pdp_and_shipping` usa `plat = p["plataforma"]` (display name: "Mercado Livre", "Netshoes", "Amazon") para lookup. O novo design precisa manter `self._by_display` acessível.
**How to avoid:** Manter `self._by_display: dict[str, Engine]` persistente apontando para as mesmas instâncias de engine, e substituir `self.engines[plat]` por `self._by_display.get(plat)` em `_enrich_pdp_and_shipping`.

### Pitfall 6: Monitor de categoria (MonitoredCategoriesPage) NÃO é alvo do D-04
**What goes wrong:** O botão "Adicionar ao monitoramento" nas três superfícies (D-07) pode ser confundido com o monitor de categoria (`/monitor/category`). D-04 é explícito: o alvo é `POST /monitor/start` (price_monitor), não `POST /monitor/category`.
**How to avoid:** O botão nas três telas chama `ApiClient.startMonitor`, nunca `ApiClient.createMonitoredCategory`. MonitoredCategoriesPage não recebe botão de "adicionar ao monitoramento" de produto individual.

### Pitfall 7: Formulário de onboarding deve passar engine inferido como campo editável
**What goes wrong:** Se o frontend não incluir o `engine` inferido como campo hidden/editável no form de confirmação, o `POST /brands/` chamado na confirmação usará `engine="auto"` — triggering um segundo `detect_engine` e possivelmente um resultado diferente.
**How to avoid:** O form de confirmação inclui o `engine` inferido pelo `/brands/identify` como campo (seletor ou display). O `POST /brands/` recebe `engine=<valor confirmado>`, nunca `engine="auto"`.

### Pitfall 8: `allow_redirects=False` em detect_engine pode não retornar HTML útil
**What goes wrong:** O Step 3 de `detect_engine` usa `allow_redirects=False` por razão de segurança (T-25-01-SR). Sites que redirecionam para subdomínio `www` retornarão um HTML de redirect vazio/simples, não a home real.
**Why it happens:** Domínios sem `www` (ex: `hugoboss.com.br` vs `www.hugoboss.com.br`) já são documentados como problemáticos (STATE.md: "sem www NÃO resolve").
**How to avoid:** Ao normalizar a URL de entrada no `/brands/identify`, adicionar `www.` se o host não começar com `www` e o Step 3 retornar redirect. Ou: informar o operador que deve colar a URL exata com `www.`. A inferência de nome terá `html=None` nesses casos — fallback de domínio.

---

## Code Examples

### Endpoint POST /brands/identify (novo)

```python
# Source: [VERIFIED: routes_brands.py — padrão dos endpoints existentes]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class IdentifyRequest(BaseModel):
    url: str

class IdentifyResponse(BaseModel):
    engine: str
    inferred_name: str
    domain: str
    warning: str | None = None  # para engine='unknown'

@router.post("/brands/identify", response_model=IdentifyResponse)
async def identify_brand(request: IdentifyRequest):
    """
    Dry-run: detecta engine + infere nome a partir da URL.
    NÃO persiste nada. D-02.
    """
    from urllib.parse import urlparse
    parsed = urlparse(request.url.strip())
    domain = parsed.netloc or parsed.path  # tolera URL sem scheme
    domain = domain.lstrip("www.") if False else domain  # preserve www — detect_engine usa domain com www
    # Normaliza: remove scheme, trailing slash
    domain = domain.rstrip("/")

    try:
        engine, home_html = await detect_engine(domain)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao acessar o domínio: {e}")

    inferred_name = infer_brand_name(home_html, domain)

    warning = None
    if engine == "unknown":
        warning = "Engine não reconhecido. Você pode selecionar manualmente antes de salvar."

    return IdentifyResponse(
        engine=engine,
        inferred_name=inferred_name,
        domain=domain,
        warning=warning,
    )
```

### ApiClient.identifyBrand (frontend)

```typescript
// Source: [VERIFIED: client.ts — padrão dos métodos existentes]
static identifyBrand(url: string) {
  return this.request<{
    engine: string;
    inferred_name: string;
    domain: string;
    warning?: string;
  }>('/brands/identify', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}
```

### ApiClient.addToMonitor (frontend — helper semântico)

```typescript
// Source: [VERIFIED: client.ts startMonitor existente]
static addToMonitor(url: string, brand: string) {
  return this.request<{ job_id: string; status: string; config: any }>(
    '/monitor/start',
    {
      method: 'POST',
      body: JSON.stringify({ url, brand, interval: 10, duration: 24 }),
    }
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Marketplaces injetados em runtime em `list_brands()` | Entradas reais em `brands.json` com `is_active` | Phase 40 (D-10) | Permite toggle via `PATCH /brands/{key}/active` existente |
| `self.engines` hardcoded no `__init__` do CrossMarketplaceService | `_active_engines()` por request via `brand_service` | Phase 40 (D-11) | Desativar marketplace surte efeito imediato na próxima busca cruzada |
| Onboarding manual (preencher todos os campos da marca) | Colar URL → identify dry-run → form pré-preenchido → confirm | Phase 40 (D-01/D-02) | Reduz fricção; operador só corrige se necessário |
| `POST /monitor/start` sempre cria novo job (uuid sem verificação) | Dedup por `normalize_url(url) + brand` antes de criar | Phase 40 (D-08/D-09) | Previne duplicatas e acumulação silenciosa de monitores redundantes |

**Deprecated/outdated:**
- Bloco `list_brands()` linhas 133-160 em `routes_brands.py`: injeção runtime de marketplaces virtuais — removido em D-10.
- `const VIRTUAL = ['mercado_livre', 'netshoes', 'amazon']` + `canToggle = !VIRTUAL.includes(b.brand_key)` em `SettingsPage`: guarda que escondia o toggle — removido em D-10.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `duration_hours` nunca é verificado no `_monitor_loop` — o loop para apenas quando `config.active = False`. | Pattern 5 / D-06 | Se existir lógica de expiração não encontrada, `duration=0` poderia parar o monitor imediatamente. Baixo risco: o código foi lido linha a linha e não há `timedelta` comparado a `duration_hours` no loop. |
| A2 | O `brand_service` é seguro para chamar de `_active_engines()` de forma síncrona dentro de um contexto async. | Pattern 7 / D-11 | `BrandManagerService.list_brands()` é síncrono (não há `await`). Chamável diretamente. [VERIFIED: brand_service.py l.95-98] |
| A3 | Instâncias de `MercadoLivreEngine`, `NetshoesEngine`, `AmazonEngine` são stateless e seguras para serem compartilhadas entre requests. | Pattern 7 / D-11 | Se carregarem estado de sessão por instância, compartilhar pode causar race condition. Requer leitura dos engines. Risco médio; se necessário, criar instâncias por request em vez de singleton. |

**Se a tabela for pequena:** A1 e A2 têm risco baixo verificável. A3 requer leitura dos arquivos de engine durante o planejamento.

---

## Open Questions

1. **Stateful dos engine instances (A3)**
   - What we know: `CrossMarketplaceService.__init__` cria as instâncias uma vez; `_fetch_all_engines` as reutiliza via `self.engines.items()`.
   - What's unclear: Se `MercadoLivreEngine`, `NetshoesEngine`, `AmazonEngine` guardam estado mutable de sessão/cookies que requer isolamento por request.
   - Recommendation: Antes de implementar D-11, ler os `__init__` de cada um dos 3 engines para confirmar stateless. Se stateful: criar instâncias em `_active_engines()` em vez de reutilizar.

2. **Campo `brand_key` no botão "Adicionar ao monitoramento" do monitor de categoria (MonitoredCategoriesPage)**
   - What we know: A superfície do monitor de categoria lista produtos (`monitorProducts`) mas o produto tem um `brand` associado ao monitor de categoria.
   - What's unclear: Qual campo exatamente corresponde ao `brand` (brand_key) para passar ao `POST /monitor/start` quando o botão é clicado em `MonitoredCategoriesPage`.
   - Recommendation: Ler `MonitoredCategoriesPage` na totalidade para confirmar o shape de `monitorProducts` e qual campo usar como `brand`.

---

## Environment Availability

Esta phase é puramente code/config-only. Não requer ferramentas externas além do que já está instalado.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `beautifulsoup4` | Inferência de nome | ✓ | `>=4.12.0` (requirements.txt) | — |
| `aiohttp` | fetch da home em detect_engine | ✓ | `>=3.9.0` (requirements.txt) | — |
| `urllib.parse` | normalização de URL | ✓ | stdlib Python | — |
| `fastapi` | novo endpoint `/brands/identify` | ✓ | `>=0.110.0` | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `pytest-asyncio` |
| Config file | `backend/pytest.ini` ou `pyproject.toml` (verificar) |
| Quick run command | `cd backend && python -m pytest tests/test_price_monitor.py tests/test_brand_active.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UX-03 | `POST /brands/identify` dry-run: retorna engine + nome, não persiste | unit | `pytest tests/test_brand_identify.py -x` | ❌ Wave 0 |
| UX-03 | `infer_brand_name` extrai nome correto nos 4 casos (JSON-LD, OG, title, domínio) | unit | `pytest tests/test_brand_identify.py::test_infer_brand_name -x` | ❌ Wave 0 |
| UX-04 | `normalize_url` descarta tracking params e preserva SKU query | unit | `pytest tests/test_url_utils.py -x` | ❌ Wave 0 |
| UX-04 | `start_monitor` com URL já ativa retorna `already_active` sem criar novo job_id | unit | `pytest tests/test_price_monitor.py::test_dedup_active -x` | ❌ Wave 0 |
| UX-04 | `start_monitor` com URL parada reativa o monitor existente | unit | `pytest tests/test_price_monitor.py::test_dedup_reactivate -x` | ❌ Wave 0 |
| UX-05 | `cross_marketplace_service._active_engines()` exclui marketplace com `is_active=False` | unit | `pytest tests/test_cross_marketplace_service.py::test_inactive_marketplace_excluded -x` | ❌ Wave 0 |
| UX-05 | `GET /brands/` retorna mercado_livre/netshoes/amazon sem injeção runtime | integration | `pytest tests/test_brand_active.py::test_marketplaces_in_brands_json -x` | ❌ Wave 0 |

### Sampling Rate
- **Por task commit:** `cd backend && python -m pytest tests/test_brand_identify.py tests/test_url_utils.py tests/test_price_monitor.py -x`
- **Por wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Suite completa verde antes do `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_brand_identify.py` — cobre UX-03 (identify dry-run + infer_brand_name)
- [ ] `backend/tests/test_url_utils.py` — cobre UX-04 (normalize_url: tracking params, SKU preservado, www, https)
- [ ] Adicionar testes em `backend/tests/test_price_monitor.py` — cobre UX-04 dedup (already_active, reactivated)
- [ ] Adicionar testes em `backend/tests/test_cross_marketplace_service.py` — cobre UX-05 (marketplace inativo excluído)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | não | endpoint existente protegido por API key existente |
| V4 Access Control | não | sem novos recursos de controle de acesso |
| V5 Input Validation | sim | URL de entrada em `/brands/identify` deve ser validada (esquema http/https, host não-vazio); body do identify não deve aceitar URLs apontando para IPs internos |
| V6 Cryptography | não | sem operações criptográficas |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via URL de marca | Spoofing / Info Disclosure | `detect_engine` já usa `allow_redirects=False` (T-25-01-SR). Validar scheme (apenas `http`/`https`) e rejeitar IPs privados (RFC1918) em `/brands/identify`. |
| Injeção via `brand_key` dos marketplaces | Tampering | `brand_service.set_active` usa `.lower().strip()` — já safe. `brand_key` dos marketplaces é validado pelo Pydantic via `DynamicBrand`. |

---

## Sources

### Primary (HIGH confidence)
- `backend/api/routes_brands.py` — leitura direta do `detect_engine` e `list_brands()` runtime injection
- `backend/services/price_monitor_service.py` — leitura direta do `_monitor_loop` e `start_monitor`
- `backend/services/cross_marketplace_service.py` — leitura direta do `__init__` e `_fetch_all_engines`
- `backend/services/brand_service.py` — leitura direta do `list_brands`, `set_active`, `add_brand`
- `backend/core/models.py` — leitura direta de `PriceMonitorConfig`, `DynamicBrand`, `BrandActiveUpdate`
- `backend/data/brands.json` — leitura direta do estado atual (sem mercado_livre/netshoes/amazon)
- `backend/requirements.txt` — confirmação de `beautifulsoup4>=4.12.0`, `aiohttp>=3.9.0`
- `frontend/src/App.tsx` — leitura direta das 3 superfícies (SearchPage, CrossMarketplacePage, MonitoredCategoriesPage) e do `VIRTUAL` guard em SettingsPage
- `frontend/src/api/client.ts` — leitura direta dos métodos existentes `startMonitor`, `getBrands`, `setBrandActive`

### Secondary (MEDIUM confidence)
- `backend/services/engines/zara_parser.py` — padrão de extração JSON-LD via BeautifulSoup usado como referência
- `backend/tests/test_price_monitor.py` — padrão de testes existentes para mock do monitor service

### Tertiary (LOW confidence)
Nenhuma.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — todos os pacotes são dependências já instaladas; verificados em requirements.txt
- Architecture patterns: HIGH — derivados de leitura direta dos arquivos de implementação; sem suposições sobre APIs externas
- Pitfalls: HIGH — cada pitfall identificado a partir de código concreto lido linha a linha
- Dedup / normalize_url: HIGH — stdlib Python, comportamento determinístico

**Research date:** 2026-06-29
**Valid until:** 2026-09-01 (stable codebase; sem dependências de pacotes de terceiros a atualizar)
