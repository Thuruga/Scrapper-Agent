# Phase 32: Engine Wake Commerce — Richards - Pesquisa

**Pesquisado em:** 2026-06-24
**Domínio:** Wake Commerce GraphQL Storefront API + integração de engine Python
**Confiança geral:** HIGH (código-fonte do repositório verificado diretamente; API Wake documentada oficialmente; o que permanece ASSUMED é exclusivamente a extração empírica do token da página da Richards — responsabilidade do spike Wave 0)

---

<user_constraints>
## Restrições do Usuário (de CONTEXT.md)

### Decisões Travadas

- **D-01 (Gate Wave 0):** O build do `WakeEngine` é gated por um spike de confirmação que demonstra que o endpoint GraphQL da Wake retorna produtos reais (título + URL + preço) com o header `TCS-Access-Token`. Alvo primário: Richards. Fallback: Shop2gether.
- **D-02 (GO threshold):** ≥1 produto com título + URL + preço retornado via GraphQL = GO.
- **D-03 (NO-GO):** Se o spike reprovar, para no gate — defere o `WakeEngine` para phase de follow-up.
- **D-04 (estrutura do spike):** `experiment.py` isolado + `REPORT.md` com veredito explícito (GO/NO-GO + evidência). Fica fora de `backend/` até o GO.
- **D-05 (aquisição do token):** Auto-extrair o `TCS-Access-Token` do storefront por loja, com override manual.
- **D-06 (armazenamento do override):** Campo opcional `wake_access_token` em `DynamicBrandCreate`/`DynamicBrand` (`core/models.py`), ao lado de `vtex_account`/`review_store_id`.
- **D-07 (falha de token):** Erro claro e diagnosticável no momento da busca, capturado pelo `_search_one` de `factory.py:92-105` como `BrandSearchResult.error`. Nunca 0 produtos silenciosos.
- **D-08 (escopo do engine):** Busca real (catálogo + preço via GraphQL) + stubs graciosos para `discover_categories`/`get_catalog` (retornam `[]` sem crash) + `calculate_shipping` → `None`.
- **D-09 (factory wiring):** `WakeEngine(brand_key)` instanciado para `engine_type == "wake"`, substituindo o guard `NotImplementedError` em `factory.py:57-60`. Import lazy (padrão `SFCCEngine` em `factory.py:48-50`).
- **D-10 (forma da busca):** Uma única query GraphQL de busca retorna título + URL + preço diretamente. Sem enriquecimento por produto.
- **D-11 (transporte HTTP):** `SessionManager.get_session()` (aiohttp compartilhado) para o POST GraphQL. Sem browser.

### Claude's Discretion

- Threshold do spike acima do mínimo (D-02, ≥1).
- Nome exato do campo de token na marca (`wake_access_token` é sugestão) e nomes de classes/constantes/markers.
- Unidade/formato do preço retornado pela GraphQL da Wake — confirmar no spike.
- Cache do token auto-extraído (evitar re-extrair a cada requisição).
- Estratégia concreta de auto-extração (de onde no HTML/JS o token aparece).
- Se a Richards é semeada em `brands.json` pela phase ou cadastrada via UI pelo operador.
- `only_in_stock` / `sort` / `max_results`: passar à GraphQL se suportado, senão filtrar client-side.
- Forma exata do retorno de `calculate_shipping` (None vs. ausência explícita).

### Ideias Deferidas (FORA DE ESCOPO)

- Monitoramento de categorias Wake (`discover_categories`/`get_catalog` reais).
- Frete/checkout Wake (`calculate_shipping` → None; sem checkout público comprometido).
- `WakeEngine` completo se o spike der NO-GO.
- Enriquecimento por produto (detail query) — não usado nesta phase (D-10).

</user_constraints>

<phase_requirements>
## Requisitos da Phase

| ID | Descrição | Suporte da Pesquisa |
|----|-----------|---------------------|
| COMP-04 | Operador consegue onboardar e buscar produtos da Richards (Wake Commerce) via API GraphQL com header `TCS-Access-Token` por loja; gated por spike de confirmação. | Endpoint confirmado documentalmente: `https://storefront-api.fbits.net/graphql`. Query `search` e query `products` com campos `productName`, `aliasComplete`, `prices.price` verificados na documentação oficial Wake. Auto-extração do token via `clientConfig.storefrontAccessToken` no HTML inline confirmada pela documentação do Storefront SDK. Estrutura do engine validada pelo análogo `SFCCEngine`/`ShopifyEngine` no código-fonte. |

</phase_requirements>

---

## Sumário

A Phase 32 entrega o `WakeEngine` — o engine Python que permite buscar produtos da Richards (e de qualquer loja Wake Commerce) via a API GraphQL pública do storefront da plataforma. O build é internamente gated pelo spike Wave 0: somente depois de demonstrar empiricamente que o endpoint `https://storefront-api.fbits.net/graphql` retorna ≥1 produto real da Richards com o header `TCS-Access-Token` correto é que o engine completo é construído.

A pesquisa confirmou documentalmente os dois pilares técnicos da phase: (1) o endpoint e o formato da query GraphQL de busca Wake são públicos e bem documentados — a query `search` retorna `productName`, `aliasComplete` e `prices.price` diretamente, sem round-trip por PDP; e (2) o `TCS-Access-Token` é um token **público de storefront**, injetado no HTML da página em um script inline como `clientConfig.storefrontAccessToken = '{{settings.access_token}}'`, e portanto auto-extraível por regex. O spike valida que esse caminho funciona empiricamente contra a Richards e Shop2gether antes de qualquer linha do engine.

O `WakeEngine` segue o mesmo molde do `SFCCEngine` (analog estrutural) e do `ShopifyEngine` (analog de transporte HTTP-API): `__init__(self, brand_key)` fino, `search()` → `BrandSearchResult` via `aiohttp` POST GraphQL, `calculate_shipping` → `None`, stubs de categoria. O código do repositório foi lido diretamente e todos os pontos de integração estão confirmados com linhas exatas.

**Recomendação principal:** Spike Wave 0 primeiro → se GO, implementar `WakeEngine` espelhando `SFCCEngine` para estrutura e `ShopifyEngine` para transporte HTTP. A query GraphQL de busca recomendada é a query `search` da Wake (não `products`) porque ela aceita um termo livre — análogo à busca por SKU do operador.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Tier Primário | Tier Secundário | Racional |
|------------|--------------|-----------------|----------|
| Spike Wave 0 (confirmação do fluxo) | Script isolado em `.planning/spikes/` | — | Fora de `backend/` até o GO, conforme D-04 |
| Auto-extração do token por loja | Backend — `WakeEngine.__init__` ou método auxiliar | `SessionManager` (aiohttp para fetch do HTML) | Token público de storefront; extraído em runtime da home page da loja |
| Busca GraphQL | Backend — `WakeEngine.search()` | `SessionManager.get_session()` | POST aiohttp para `storefront-api.fbits.net/graphql` com header TCS-Access-Token |
| Quality Gates (Pydantic) | Backend — `BaseEngine.validate_single` / `validate_and_filter` | — | Herdado do contrato `BaseEngine`, aplicado antes do retorno |
| Filtro CAT-01 (moda masculina) | Backend — `BaseEngine.filter_mens_fashion` | — | Herdado, aplicado antes do retorno |
| Wiring na factory | Backend — `EngineFactory.get_engine` | — | Import lazy `WakeEngine`, substitui guard `NotImplementedError` L57-60 |
| Persistência do token de override | `backend/data/brands.json` via `DynamicBrandCreate.wake_access_token` | `brand_service` | Campo opcional, como `vtex_account`/`review_store_id` |
| Stubs de categoria | Backend — `WakeEngine.discover_categories`/`get_catalog` | — | Retornam `[]` sem crash (D-08) |
| Frete | Backend — `WakeEngine.calculate_shipping` → `None` | — | Sem checkout público comprometido (D-08) |

---

## Stack Padrão

### Core (já presente no projeto — nenhuma instalação nova necessária)

| Biblioteca | Versão instalada | Propósito | Por que padrão |
|------------|-----------------|-----------|---------------|
| `aiohttp` | 3.13.3 | POST GraphQL assíncrono para `storefront-api.fbits.net/graphql` | Já usado por `ShopifyEngine` e `SessionManager`; suporta headers customizados e JSON body diretamente |
| `pydantic` | 2.12.5 | Validação dos produtos via `RawProductBronze` (Quality Gates) | Contrato `BaseEngine`; campo `wake_access_token` é Optional no modelo |
| `pytest` + `pytest-asyncio` | 9.0.3 / 1.3.0 | Testes unitários herméticos (mocks de `SessionManager`) | Padrão do repositório |
| `beautifulsoup4` | 4.14.3 | Parsing do HTML da home page para extrair `storefrontAccessToken` | Já no projeto; padrão para parsing HTML |

### Sem dependências externas novas

Esta phase não requer instalação de novos pacotes. O transporte HTTP (aiohttp + SessionManager), o parsing HTML (bs4) e os Quality Gates (pydantic) já estão no ambiente.

## Auditoria de Legitimidade de Pacotes

> Nenhum pacote novo é instalado nesta phase. Todas as dependências já estão presentes no ambiente Python 3.14.3 do projeto. A verificação slopcheck foi executada sobre os pacotes que o `WakeEngine` usa em runtime:

| Pacote | Registry | slopcheck | Disposição |
|--------|----------|-----------|-----------|
| aiohttp | PyPI | [OK] | Aprovado (já instalado 3.13.3) |
| pydantic | PyPI | [OK] | Aprovado (já instalado 2.12.5) |
| pytest | PyPI | [OK] | Aprovado (já instalado 9.0.3) |
| beautifulsoup4 | PyPI | [OK] | Aprovado (já instalado 4.14.3) |
| pytest-asyncio | PyPI | [OK] | Aprovado (já instalado 1.3.0) |

**Pacotes removidos por veredicto [SLOP]:** nenhum
**Pacotes flagados como suspeitos [SUS]:** nenhum

---

## Padrões de Arquitetura

### Diagrama de Fluxo do Sistema

```
Operador / Agendador
         │
         ▼
EngineFactory.get_engine("wake")  [factory.py L57-60 substituído]
         │  import lazy: from services.engines.wake_engine import WakeEngine
         ▼
WakeEngine(brand_key="richards")
         │
         ├─► _resolve_token(brand_key)
         │       │
         │       ├─► brand_service.get_brand(brand_key).wake_access_token  [override]
         │       │         se presente: usa override → retorna token
         │       │
         │       └─► auto-extração: GET https://{domain}
         │               SessionManager.get_session() → aiohttp GET
         │               bs4 parse HTML → regex clientConfig.storefrontAccessToken
         │               se falha: raise TokenResolutionError  →  BrandSearchResult.error
         │
         ├─► WakeEngine.search(query, max_results, ...)
         │       │
         │       ▼
         │   POST https://storefront-api.fbits.net/graphql
         │   Header: TCS-Access-Token = <token>
         │   Body: { "query": "query { search(query: \"...\") { products(first: N) {
         │           edges { node { productName aliasComplete prices { price }
         │                         images { url } available } } } } }" }
         │       │
         │       ▼
         │   JSON response → parse nodes → lista de dicts
         │       │
         │       ├─► filter_mens_fashion(produtos)   [CAT-01]
         │       ├─► validate_single(p) / validate_and_filter   [Quality Gate Pydantic]
         │       └─► SearchProductResult(brand, product_name, url, price_full, image_url)
         │
         ▼
BrandSearchResult(brand_key, brand_name, products=[...])
         │
         ▼  (ou se falha):
BrandSearchResult(brand_key, brand_name, error="...")
         └─ capturado por _search_one try/except (factory.py:92-105) — gather não cai
```

### Estrutura de Arquivos Recomendada

```
backend/
├── services/engines/
│   ├── wake_engine.py      # WakeEngine — engine principal (criado nesta phase)
│   └── factory.py          # editar L57-60: substituir NotImplementedError por WakeEngine
├── core/
│   └── models.py           # editar: adicionar wake_access_token Optional[str] em DynamicBrandCreate/DynamicBrand
└── tests/
    └── test_wake_engine.py  # testes herméticos (criados nesta phase)

.planning/spikes/
└── 007-wake-graphql-token-confirmation/   # spike Wave 0 (fora de backend/)
    ├── experiment.py                       # isolado e reprodutível
    └── REPORT.md                           # veredito explícito GO/NO-GO
```

### Padrão 1: Estrutura do WakeEngine (analog direto do SFCCEngine)

```python
# Source: backend/services/engines/sfcc_engine.py (lido diretamente)
# backend/services/engines/wake_engine.py

from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional
from core.models import BrandSearchResult, SearchProductResult
from services.engines.base_engine import BaseEngine

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://storefront-api.fbits.net/graphql"
DEFAULT_MAX_RESULTS = 10

class WakeEngine(BaseEngine):
    def __init__(self, brand_key: str) -> None:
        self.brand_key = brand_key
        self._token_cache: Optional[str] = None  # cache por instância (Claude's Discretion)

    def get_engine_name(self) -> str:
        return "Wake"

    async def search(
        self,
        query: str,
        max_results: int = DEFAULT_MAX_RESULTS,
        sort: Optional[str] = None,
        only_in_stock: bool = False,
        zipcode: Optional[str] = None,
        include_shipping: bool = False,
    ) -> BrandSearchResult:
        token = await self._resolve_token()
        if not token:
            raise ValueError(
                f"Token Wake não resolvido para '{self.brand_key}'. "
                "Configure wake_access_token na marca ou verifique o storefront."
            )
        # POST GraphQL ...
        ...

    async def calculate_shipping(self, product: Any, zipcode: str) -> Optional[Dict[str, Any]]:
        return None  # D-08: sem checkout público

    async def discover_categories(self) -> List[Dict[str, Any]]:
        return []  # D-08: stub gracioso

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return []  # D-08: stub gracioso

    async def run_bulk_scrape(self, category_url: str, log_callback=None, cancel_event=None, zipcode=None, include_shipping=False):
        return  # stub: yield nada

    async def get_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        return None  # stub

    async def _resolve_token(self) -> Optional[str]:
        # 1. Override manual (D-06)
        # 2. Auto-extração do HTML (D-05)
        # 3. None → D-07 erro claro
        ...
```

### Padrão 2: Factory wiring (lazy import — espelha L48-50)

```python
# Source: backend/services/engines/factory.py L48-50 e L57-60 (lidos diretamente)
# Linha 57-60 atual (a substituir):
#   if engine_type == "wake":
#       raise NotImplementedError(...)

# Linha nova (espelha SFCCEngine L48-50):
if engine_type == "wake":
    from services.engines.wake_engine import WakeEngine  # noqa: PLC0415
    return WakeEngine(brand_key)
```

### Padrão 3: Campo opcional no modelo (espelha vtex_account / review_store_id)

```python
# Source: backend/core/models.py L207-226 (lido diretamente)
# Adicionar em DynamicBrandCreate:
wake_access_token: Optional[str] = None  # override manual do token público de storefront Wake
```

### Padrão 4: Query GraphQL de busca Wake

```graphql
# Source: wakecommerce.readme.io/docs/storefront-api-search.md (CITADO)
# Campos: productName (título), aliasComplete (URL relativa), prices.price (preço),
#          images.url (imagem), available (estoque)
query WakeSearch($q: String!, $first: Int!) {
  search(query: $q) {
    products(first: $first) {
      edges {
        node {
          productName
          aliasComplete
          prices {
            price
            listPrice
          }
          images {
            url
          }
          available
        }
      }
    }
  }
}
```

> **ATENÇÃO:** O nome exato dos campos e a disponibilidade de `images` dentro de `search.products` NÃO foi confirmado empiricamente — apenas na documentação do endpoint `products` (query diferente). O spike Wave 0 valida se `search.products.edges.node.images` existe, ou se `aliasComplete` é retornado dentro do contexto `search`. O campo `prices.price` foi confirmado como presente em `search` via documentação (CITADO). O campo `aliasComplete` para URL foi confirmado em `products` (CITADO) — sua presença em `search` é ASSUMED até o spike.

### Padrão 5: Auto-extração do `TCS-Access-Token` via HTML

```python
# Source: wakecommerce.readme.io/docs/storefront-sdk (CITADO — padrão de injeção do SDK)
# O SDK Wake injeta o token em um inline script com este padrão:
# <script>
#   const clientConfig = {
#       storefrontAccessToken: 'tcs_loja_xxxxxxxxxxxxxxxx',
#       storeUrl: '...'
#   };
# </script>

import re

_TOKEN_RE = re.compile(
    r"""storefrontAccessToken\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

def extract_token_from_html(html: str) -> Optional[str]:
    """
    Extrai o storefrontAccessToken do inline script do SDK Wake.
    Retorna None se não encontrado — caller trata como ausência de token.
    """
    match = _TOKEN_RE.search(html)
    return match.group(1) if match else None
```

> **ASSUMED:** O token `storefrontAccessToken` injetado pelo SDK Wake no HTML equivale ao `TCS-Access-Token` que o header da GraphQL API espera. O padrão de injeção `clientConfig.storefrontAccessToken = '{{settings.access_token}}'` foi confirmado na documentação do Storefront SDK (CITADO). A correspondência exata entre esse valor e o header `TCS-Access-Token` aceito pelo endpoint GraphQL é ASSUMED — confirmada pelo spike (o spike envia o token extraído e verifica se a resposta retorna produtos reais).

> **ALTERNATIVA de extração:** A documentação menciona que a CLI local usa o token com o prefixo `tcs_loja_xxxxxx`. Se `storefrontAccessToken` não estiver no HTML (ex.: store com template custom), um fallback seria buscar por regex `tcs_[a-zA-Z0-9_]+` em qualquer `<script>` inline. Ambas as estratégias são candidatas ao spike.

### Anti-Padrões a Evitar

- **Usar o caminho VTEX para lojas Wake:** O VTEX API (`/api/catalog_system/pub/...`) retorna 0 produtos para lojas Wake (razão de existir este engine). O `WakeEngine` nunca deve usar `VTEXEngine` internamente.
- **Construir o engine sem o spike:** D-03 proíbe explicitamente. Se o spike der NO-GO, o engine não é construído.
- **Hardcoded global do token:** D-06 — token por loja (campo opcional na marca), nunca uma constante global.
- **0 produtos silenciosos no erro de token:** D-07 — o erro deve aparecer em `BrandSearchResult.error`, nunca como lista vazia sem mensagem.
- **Import circular:** Usar import lazy dentro de `get_engine` (já estabelecido no padrão do `SFCCEngine`, `factory.py:48-50`).
- **Enriquecimento por PDP:** D-10 — a query `search` da Wake retorna preço diretamente. Sem round-trip PDP (diferente do SFCC).

---

## Não Construir na Mão

| Problema | Não Construir | Usar Em Vez | Por quê |
|----------|--------------|-------------|---------|
| Cliente HTTP assíncrono | Cliente HTTP próprio | `SessionManager.get_session()` → `aiohttp.ClientSession` | Já existe, compartilhado, com pool de conexões (limit=50, ttl_dns_cache=300) |
| Validação de campos de produto | Validação manual de dicts | `BaseEngine.validate_and_filter` / `validate_single` (`RawProductBronze`) | Quality Gate Pydantic já implementado; rejeita produtos sem url/raw_title/price_full/image_url |
| Filtro de categorias femininas | Lógica de blocklist própria | `BaseEngine.filter_mens_fashion` | Blocklist mantida centralmente; word-boundary regex; consistência CAT-01 |
| Serialização de marca | JSON manual | `brand_service.get_brand()` / `brand_service.save_brand()` | Persistência atômica em `data/brands.json`, validada por Pydantic |
| Captura de erros por marca | Try/except no engine | `factory._search_one` try/except (L92-105) | Já captura qualquer `Exception` do engine e retorna `BrandSearchResult.error`; evita derrubar o `asyncio.gather` |

---

## Inventário de Estado em Runtime

> Esta phase NÃO é uma refatoração/renomeação. Não há strings a renomear em bases de dados ou configurações de runtime. O inventário abaixo confirma que não há estado persistido a migrar.

| Categoria | Itens Encontrados | Ação Necessária |
|-----------|-----------------|-----------------|
| Dados armazenados | `data/brands.json` — Richards ainda não está cadastrada (confirmado: o CONTEXT.md diz "Richards ainda não está em data/brands.json") | Nenhuma migração; a Richards é semeada/cadastrada durante a validação da phase |
| Config de serviço em runtime | Nenhuma — `factory.py` usa guard `NotImplementedError` para wake (linha 57-60); não há config ativa | Substituição de código apenas |
| Estado registrado no SO | Nenhum — o projeto não usa Task Scheduler, systemd ou pm2 para o engine Wake | Nenhuma |
| Segredos/env vars | `TCS-Access-Token` é token público de storefront — não é segredo de servidor; pode ser commitado como campo de marca | Campo opcional em `brands.json` (git-tracked); aceitável (CONTEXT.md D-06) |
| Artefatos de build | `backend/__pycache__/` — recompilado automaticamente pelo Python ao criar `wake_engine.py` | Nenhuma ação manual |

**Nada encontrado em nenhuma categoria que exija migração de dados ou re-registro de serviços.**

---

## Armadilhas Comuns

### Armadilha 1: Token de Override ≠ Token Auto-Extraído (ambiguidade de campo)

**O que acontece de errado:** O campo `wake_access_token` em `DynamicBrandCreate` guarda o override manual; o valor auto-extraído do HTML é cacheado em memória. Se o código confundir os dois caminhos, pode enviar `None` sem tentar a auto-extração, ou usar o cache expirado indefinidamente.

**Por que acontece:** A lógica de resolução tem dois caminhos (override manual → auto-extração) e um cache opcional — se implementada como uma cadeia de if/else sem separação clara de responsabilidade, a ordem pode ser invertida.

**Como evitar:** Implementar `_resolve_token(brand_key)` como método único com precedência clara: (1) override de `brand_data.wake_access_token`; (2) cache em memória; (3) auto-extração via GET no storefront; (4) raise `ValueError` claro. O spike valida o caminho (3) antes da implementação.

**Sinais de alerta:** `BrandSearchResult.error` contendo "Token Wake não resolvido" sem que o operador tivesse configurado o override manual — indica que a auto-extração nunca foi tentada.

### Armadilha 2: `aliasComplete` vs. URL absoluta

**O que acontece de errado:** A API Wake retorna `aliasComplete` como um caminho relativo (ex.: `"produto/camisa-123"`) — não como URL absoluta. Se o engine montar a URL como `https://storefront-api.fbits.net/produto/camisa-123` em vez de `https://{domain}/{aliasComplete}`, a URL do produto fica inválida.

**Por que acontece:** A documentação descreve `aliasComplete` como "full alias considering admin URL configuration" sem especificar se inclui o domínio base. O spike deve verificar o formato exato retornado.

**Como evitar:** No parser Wake, montar sempre a URL completa como `f"https://{domain}/{alias.lstrip('/')}"` usando o domínio registrado da marca. O spike imprime o valor bruto de `aliasComplete` para confirmar o formato.

**Sinais de alerta:** URLs em `SearchProductResult.url` sem esquema (`https://`) ou apontando para `storefront-api.fbits.net` em vez do domínio da loja.

### Armadilha 3: Campo `images` dentro de `search.products` (não confirmado empiricamente)

**O que acontece de errado:** A documentação confirma `images { url }` na query `products` (browse por categoria/filtro), mas dentro da query `search` (busca por termo) os campos disponíveis nos nós podem diferir. Se `images` não estiver disponível em `search.products.edges.node`, o Quality Gate `validate_single` rejeita o produto (campo `image_url` obrigatório em `RawProductBronze`).

**Por que acontece:** As duas queries da Wake (`search` e `products`) têm tipos de retorno distintos. A documentação listou `images` explicitamente apenas em `products`.

**Como evitar:** O spike deve incluir `images { url }` na query de teste e verificar se o campo está presente no retorno. Se ausente, o engine usa `None` para `image_url` e aceita que o Quality Gate rejeitará o produto (ou adiciona um fallback de imagem via campo `aliasComplete`). Como alternativa, o planner pode optar pela query `products(filters: {search: [...]})` em vez de `search(query: ...)` — ambas são candidatas.

**Sinais de alerta:** 0 produtos retornados para uma busca que empiricamente deveria ter resultados, sem `error` no `BrandSearchResult`.

### Armadilha 4: `prices.price` vs. `buyBox.minimumPrice` (unidade e semântica)

**O que acontece de errado:** A Wake expõe preço em dois campos: `prices.price` (preço atual do produto no contexto do storefront) e `buyBox.minimumPrice` (melhor preço entre vendedores do marketplace). Para a Richards (loja própria Wake, não marketplace), `prices.price` é o campo correto. Usar `buyBox.minimumPrice` pode retornar `null` se a loja não tiver concorrência de vendedores.

**Por que acontece:** A documentação da query `search` mostrou `buyBox.minimumPrice` como exemplo principal; `prices.price` é o campo do nó de produto individual. A unidade é aparentemente em reais como float (ex.: `799.0`), não em centavos — ao contrário da VTEX (Phase 33 usa centavos→reais). Mas isso é ASSUMED.

**Como evitar:** O spike imprime o valor raw de `prices.price` para uma busca real, confirma que é float em reais (não centavos). O parser aplica passthrough para floats positivos (padrão de `parse_price_br` numérico).

**Sinais de alerta:** Preço `price_full = 79900.0` quando o produto custa R$ 799,00 (indica que o valor está em centavos e precisa de divisão por 100).

### Armadilha 5: Cache de token e concorrência (asyncio)

**O que acontece de errado:** Se o `_token_cache` for compartilhado entre instâncias de `WakeEngine` (ex.: como variável de classe) ou se duas coroutines tentarem auto-extrair o token simultaneamente, pode haver race condition ou um token de uma marca sendo enviado para outra.

**Por que acontece:** `asyncio.gather` executa buscas em paralelo para todas as marcas; se duas marcas Wake forem buscadas ao mesmo tempo e compartilharem um cache mal escoped, o token da primeira pode vazar para a segunda.

**Como evitar:** Cache como atributo de instância (`self._token_cache`), não de classe. Como cada `get_engine(brand_key)` instancia um novo `WakeEngine(brand_key)`, o cache é por instância e por chamada de `search_all_brands`. Se for necessário cache de longa duração, usar um dict `{brand_key: token}` no escopo do módulo com lock asyncio.

**Sinais de alerta:** Uma marca Wake recebendo `BrandSearchResult.error` com "Token inválido" imediatamente após outra marca Wake ter buscado com sucesso.

---

## Evidências de Código do Repositório

### factory.py — Guard Wake atual (L57-60) a substituir

```python
# [VERIFIED: repositório lido diretamente — factory.py L57-60]
if engine_type == "wake":
    raise NotImplementedError(
        f"Engine 'wake' para '{brand_key}' ainda não disponível (Phase 32 pendente)."
    )
```

### factory.py — _search_one (L92-105) que captura o erro de token como D-07

```python
# [VERIFIED: repositório lido diretamente — factory.py L92-105]
async def _search_one(brand_key: str) -> BrandSearchResult:
    try:
        engine = self.get_engine(brand_key)
        return await engine.search(
            query=query.strip(),
            max_results=max_per_brand,
            sort=sort,
            only_in_stock=only_in_stock,
            zipcode=zipcode,
            include_shipping=include_shipping
        )
    except Exception as e:
        return BrandSearchResult(brand_key=brand_key, brand_name=brand_key, error=str(e))
```

### models.py — DynamicBrandCreate (L207-226) — campo wake_access_token a adicionar

```python
# [VERIFIED: repositório lido diretamente — models.py L207-226]
# Campos opcionais existentes (padrão para wake_access_token):
review_provider: Optional[str] = "none"
review_store_id: Optional[str] = None
vtex_account: Optional[str] = None
engine: Optional[str] = "vtex"
logo_url: Optional[str] = None
# A adicionar (D-06):
wake_access_token: Optional[str] = None
```

### test_sfcc_engine.py — TestSFCCFactory.test_factory_wake_still_raises (L235-249)

```python
# [VERIFIED: repositório lido diretamente — test_sfcc_engine.py L235-249]
# Este teste DEVE passar a falhar (e ser deletado/substituído) quando o WakeEngine for implementado.
def test_factory_wake_still_raises(self):
    """factory.py guard for 'wake' is preserved (Pitfall 4 — not a delete)."""
    # Após a Phase 32, este teste deixa de existir ou é substituído por
    # test_factory_returns_wake_engine() com assertIsInstance(..., WakeEngine)
```

---

## Estado da Arte

| Abordagem Antiga | Abordagem Atual | Quando Mudou | Impacto |
|-----------------|----------------|--------------|---------|
| VTEX API para lojas Wake (0 produtos) | GraphQL `storefront-api.fbits.net` com TCS-Access-Token | Phase 32 (esta phase) | Produtos reais da Richards em vez de lista vazia |
| Guard `NotImplementedError` para `wake` | `WakeEngine(brand_key)` plugado na `EngineFactory` | Phase 32 (esta phase) | `engine_type == "wake"` entra no gather de buscas |
| Token Wake não configurável | Campo opcional `wake_access_token` + auto-extração | Phase 32 (esta phase) | Zero-config onboarding para lojas Wake padrão |

**Descontinuado/desatualizado:**
- Guard `NotImplementedError` para `wake` em `factory.py:57-60`: substituído por `WakeEngine(brand_key)` após GO do spike.
- Teste `test_factory_wake_still_raises` em `test_sfcc_engine.py:235-249`: deixa de ser válido após a implementação do `WakeEngine` e deve ser substituído por teste positivo.

---

## Log de Suposições (ASSUMED)

| # | Afirmação | Seção | Risco se Errado |
|---|-----------|-------|-----------------|
| A1 | `storefrontAccessToken` no inline script do SDK Wake é o mesmo valor que deve ser enviado como header `TCS-Access-Token` para a GraphQL API | Padrão 5 (Auto-extração) | Spike retorna 401/403; operador precisa configurar override manual; auto-extração não funciona sem ajuste na regex ou no campo buscado |
| A2 | O campo `aliasComplete` está disponível dentro de `search.products.edges.node` (não apenas em `products.nodes`) | Padrão 4 (Query GraphQL) | URL de produto fica indisponível na busca; engine precisa de query alternativa (`products` com `filters: {search: [...]}`) ou enriquecimento adicional |
| A3 | O campo `images { url }` está disponível dentro de `search.products.edges.node` | Armadilha 3 | Quality Gate rejeita todos os produtos (image_url obrigatória em RawProductBronze); engine precisa de query alternativa ou campo image desabilitado no Quality Gate para Wake |
| A4 | `prices.price` retorna o valor em reais como float (ex.: `799.0`), não em centavos | Armadilha 4 | Parser divide por 100 desnecessariamente (preço errado na UI) ou não divide (preço 100x maior) |
| A5 | A Richards (www.richards.com.br) usa o SDK Wake padrão que injeta `clientConfig.storefrontAccessToken` no HTML da home page | Padrão 5 | Regex de extração não encontra o token; operador precisa configurar override manual; auto-extração funciona só no Shop2gether |
| A6 | A query `search` da Wake não requer autenticação de usuário além do header `TCS-Access-Token` (i.e., não exige reCAPTCHA nem cookie de sessão para buscas genéricas) | Padrão 4 (Query GraphQL) | Spike recebe 403 ou resposta vazia mesmo com token correto; engine não é viável sem bypass |

**Se esta tabela estiver vazia:** todas as afirmações foram verificadas ou citadas. Não é o caso aqui — A1 a A6 devem ser validadas pelo spike Wave 0 antes do build do engine.

---

## Convenção de Spikes (D-04)

**Fonte:** `.planning/spikes/CONVENTIONS.md` + análise de spikes 001-006 [VERIFIED: repositório lido diretamente]

### Layout Exato

```
.planning/spikes/007-wake-graphql-token-confirmation/
├── experiment.py    # Python puro, rodado da raiz: python .planning/spikes/007-.../experiment.py
└── REPORT.md        # gerado pelo script; veredito explícito GO/NO-GO
```

Opcionalmente: `README.md` (frontmatter + trilha de investigação + veredito).

### Convenções do `experiment.py`

```python
# [VERIFIED: .planning/spikes/001-brand-gate-impact/experiment.py L27-29 (padrão)]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
```

- Reutilizar serviços reais do projeto quando possível (ex.: `SessionManager.get_session()` para aiohttp).
- Saída dupla: stdout (resumo) + `REPORT.md` (evidência estruturada).
- **Sem dependências novas** — o que o projeto já tem (aiohttp, bs4, pydantic) basta.

### Formato do REPORT.md (veredito GO/NO-GO)

```markdown
# Spike 007 — Wake GraphQL Token Confirmation

## Veredito
**GO** ← (ou NO-GO)

## Evidência
- Endpoint: https://storefront-api.fbits.net/graphql
- Header: TCS-Access-Token: tcs_loja_xxxx (extraído de: <URL da home>)
- Query: search(query: "camisa")
- Resposta (≥1 produto): [{ productName: "Camisa ...", aliasComplete: "...", prices.price: 799.0 }]

## Campos confirmados
| Campo | Disponível | Valor exemplo |
|-------|-----------|---------------|
| productName | sim | "Camisa Slim..." |
| aliasComplete | sim | "produto/camisa-slim-123" |
| prices.price | sim | 799.0 |
| images.url | sim/não | "https://..." |
| available | sim/não | true |

## Formato do preço
- Numérico float em reais (não centavos): **CONFIRMADO / NÃO CONFIRMADO**

## Token auto-extraído
- Estratégia: regex `storefrontAccessToken` no inline script
- Token encontrado em: <URL onde foi buscado>
- Prefixo observado: tcs_loja_... / outro

## Alvo testado
- [ ] Richards (www.richards.com.br) — primário
- [ ] Shop2gether (www.shop2gether.com.br) — fallback
```

---

## Perguntas em Aberto

1. **`aliasComplete` dentro de `search.products.edges.node`?**
   - O que sabemos: `aliasComplete` está documentado para a query `products`. A query `search` retorna nós de produto, mas os campos disponíveis podem diferir.
   - O que está incerto: Se `aliasComplete` está disponível dentro de `search.products`, ou se é necessário usar a query `products(filters: {search: [...]})` em vez de `search(query: ...)`.
   - Recomendação: O spike testa ambas as queries e reporta qual retorna `aliasComplete` com URL válida.

2. **`images { url }` dentro de `search.products.edges.node`?**
   - O que sabemos: `images { url }` está documentado para `products.nodes`. A query `search` pode não expor `images` nos nós.
   - O que está incerto: Se o campo existe no tipo de nó retornado por `search`.
   - Recomendação: O spike inclui `images { url }` na query e verifica se retorna ou gera erro de schema. Se ausente, o planner deve decidir: (a) usar `products` em vez de `search`, ou (b) relaxar o Quality Gate para `image_url` no contexto Wake.

3. **Prefixo e localização do token na home da Richards vs. Shop2gether**
   - O que sabemos: O SDK Wake injeta `storefrontAccessToken` em um `<script>` inline como `clientConfig.storefrontAccessToken = '{{settings.access_token}}'`. Isso é o padrão documentado.
   - O que está incerto: Se a Richards usa exatamente este padrão ou um template customizado onde o token aparece com nome/posição diferente.
   - Recomendação: O spike testa a regex `storefrontAccessToken\s*:\s*['"]([^'"]+)['"]` contra o HTML real da home da Richards e Shop2gether e reporta se encontrou e qual foi o valor (sem imprimir o token completo em texto claro no REPORT.md).

---

## Disponibilidade do Ambiente

| Dependência | Requerida por | Disponível | Versão | Fallback |
|-------------|--------------|-----------|--------|---------|
| Python 3.14.3 | WakeEngine, spike | ✓ | 3.14.3 | — |
| aiohttp | POST GraphQL, auto-extração do token | ✓ | 3.13.3 | — |
| pydantic | Quality Gates, modelos | ✓ | 2.12.5 | — |
| beautifulsoup4 | Parsing HTML para extração do token | ✓ | 4.14.3 | — |
| pytest + pytest-asyncio | Testes herméticos | ✓ | 9.0.3 / 1.3.0 | — |
| Acesso à internet (spike) | GET www.richards.com.br, POST storefront-api.fbits.net | ASSUMED ✓ | — | Shop2gether como fallback |
| `TCS-Access-Token` válido (spike) | Confirmação GraphQL | ASSUMED — auto-extraído durante o spike | — | Override manual via campo da marca |

**Dependências ausentes sem fallback:** nenhuma (para o build do engine).

**Dependências ausentes com fallback:**
- Token da Richards: se o token não puder ser auto-extraído, o spike usa Shop2gether (D-01) ou o operador fornece o token via override manual.

---

## Arquitetura de Validação

### Framework de Testes

| Propriedade | Valor |
|-------------|-------|
| Framework | pytest 9.0.3 + pytest-asyncio 1.3.0 |
| Arquivo de config | `pytest.ini` ou `pyproject.toml` (verificar existente no repo) |
| Comando rápido | `python -m pytest backend/tests/test_wake_engine.py -q` |
| Suite completa | `python -m pytest backend/tests/ -q` |

### Mapa Requisitos → Testes

| Req ID | Comportamento | Tipo de Teste | Comando Automatizado | Arquivo Existe? |
|--------|--------------|---------------|---------------------|----------------|
| COMP-04 SC-1 | Spike confirma GO via GraphQL+token | Manual (spike) | `python .planning/spikes/007-.../experiment.py` | ❌ Wave 0 |
| COMP-04 SC-2 | `WakeEngine.search()` retorna ≥1 produto real (title+url+price) com SessionManager mockado | unit | `pytest backend/tests/test_wake_engine.py::TestWakeEngineSearch::test_search_returns_products -x` | ❌ Wave 0 |
| COMP-04 SC-3 | `EngineFactory.get_engine` para brand com `engine="wake"` retorna `WakeEngine` (não `NotImplementedError`) | unit | `pytest backend/tests/test_wake_engine.py::TestWakeFactory::test_factory_returns_wake_engine -x` | ❌ Wave 0 |
| COMP-04 SC-4 | Token ausente/erro → `BrandSearchResult.error` com mensagem clara (não 0 produtos silenciosos) | unit | `pytest backend/tests/test_wake_engine.py::TestWakeTokenFailure::test_missing_token_returns_error -x` | ❌ Wave 0 |
| COMP-04 SC-4 | `calculate_shipping` retorna `None` (sem badge "Frete Grátis" indevido) | unit | `pytest backend/tests/test_wake_engine.py::TestWakeEngineSearch::test_calculate_shipping_returns_none -x` | ❌ Wave 0 |
| D-06 | `wake_access_token` opcional em `DynamicBrandCreate`/`DynamicBrand` sem quebrar marcas existentes | unit | `pytest backend/tests/test_wake_engine.py::TestWakeModels::test_model_wake_token_optional -x` | ❌ Wave 0 |
| D-08 | `discover_categories()` retorna `[]` sem crash | unit | `pytest backend/tests/test_wake_engine.py::TestWakeStubs::test_discover_categories_stub -x` | ❌ Wave 0 |
| Regressão | Suite completa verde (225 testes existentes + novos Wake) | regression | `python -m pytest backend/tests/ -q` | ✓ (225 passando) |

### Taxa de Amostragem (Nyquist)

- **Por commit de tarefa:** `python -m pytest backend/tests/test_wake_engine.py -q --tb=short`
- **Por merge de wave:** `python -m pytest backend/tests/ -q`
- **Gate da phase:** Suite completa verde antes de `/gsd-verify-work`

### Gaps do Wave 0

- [ ] `backend/tests/test_wake_engine.py` — cobre SC-2, SC-3, SC-4, D-06, D-08
- [ ] `.planning/spikes/007-wake-graphql-token-confirmation/experiment.py` — spike isolado
- [ ] `.planning/spikes/007-wake-graphql-token-confirmation/REPORT.md` — gerado pelo spike

*Infraestrutura de testes existente (pytest, pytest-asyncio, conftest implícito) cobre todos os requisitos — apenas os novos arquivos de teste precisam ser criados.*

---

## Domínio de Segurança

### Categorias ASVS Aplicáveis

| Categoria ASVS | Aplica | Controle Padrão |
|----------------|--------|----------------|
| V2 Autenticação | Parcial | `TCS-Access-Token` é token de storefront público (não credencial de usuário); sem autenticação de sessão no engine |
| V3 Gerenciamento de Sessão | Não | Engine stateless; `SessionManager` reusa sessão aiohttp sem estado de usuário |
| V4 Controle de Acesso | Não | Engine não expõe endpoints próprios; acesso via `EngineFactory` existente |
| V5 Validação de Entrada | Sim | `query` do usuário é passado literalmente para a GraphQL da Wake — sem interpolação shell; risco de injection é da Wake, não nosso |
| V6 Criptografia | Não | Token público de storefront; sem segredos de servidor ou criptografia customizada |

### Padrões de Ameaça Conhecidos para a Stack Wake/GraphQL

| Padrão | STRIDE | Mitigação Padrão |
|--------|--------|-----------------|
| Token de storefront exposto em `brands.json` git-tracked | Information Disclosure | Aceitável por design (D-06): é token público de storefront, não segredo de servidor — o mesmo valor é entregue no HTML da página a qualquer visitante |
| Query injection via `query` string | Tampering | A query GraphQL usa variáveis (`$q: String!`) — não interpolação de string; a Wake é responsável pelo sanitamento server-side |
| Redirect aberto no GET da home page (extração do token) | Elevation of Privilege | Usar `allow_redirects=False` no aiohttp GET (mesmo padrão de T-25-01-SR já aplicado em `routes_brands.py:44`) |
| 0 produtos silenciosos (D-07) | Repudiation | `_search_one` captura qualquer exceção e retorna `BrandSearchResult.error`; o operador vê o erro explicitamente |

---

## Fontes

### Primárias (confiança HIGH — código lido diretamente)

- `backend/services/engines/factory.py` — guard `wake` L57-60; `_search_one` L92-105; import lazy SFCCEngine L48-50
- `backend/services/engines/base_engine.py` — contrato `BaseEngine`; `validate_and_filter`; `validate_single`; `filter_mens_fashion`
- `backend/services/engines/sfcc_engine.py` — analog estrutural completo (padrão de engine não-VTEX com import lazy)
- `backend/services/engines/shopify_engine.py` — analog de transporte HTTP-API; `SessionManager.get_session()` para aiohttp
- `backend/core/models.py` — `DynamicBrandCreate`/`DynamicBrand`; `BrandSearchResult`; `RawProductBronze`; `SearchProductResult`
- `backend/core/session_manager.py` — `SessionManager.get_session()` aiohttp compartilhado
- `backend/services/brand_service.py` — `get_brand`; `save_brand`; `add_brand`
- `backend/api/routes_brands.py` — `detect_engine`; `create_brand`
- `backend/tests/test_sfcc_engine.py` — padrão de testes herméticos; seam de mock; `test_factory_wake_still_raises` a substituir
- `backend/tests/test_engine_detection.py` — padrão `_make_mock_session` / `_make_mock_response`
- `.planning/spikes/CONVENTIONS.md` — layout e convenções de spike
- `.planning/spikes/001-brand-gate-impact/experiment.py` — padrão `ROOT / sys.path / os.chdir`

### Secundárias (confiança MEDIUM — documentação oficial Wake)

- [wakecommerce.readme.io — Storefront API Search](https://wakecommerce.readme.io/docs/storefront-api-search.md) — query `search`, campos `productName`, `prices.price`
- [wakecommerce.readme.io — Storefront API Products](https://wakecommerce.readme.io/docs/storefront-api-products.md) — campos `aliasComplete`, `images { url }`, `prices.price`
- [wakecommerce.readme.io — Storefront SDK](https://wakecommerce.readme.io/docs/storefront-sdk) — padrão `clientConfig.storefrontAccessToken = '{{settings.access_token}}'` no HTML inline
- [wakecommerce.readme.io — Explorando a API](https://wakecommerce.readme.io/docs/storefront-api-explorando-a-api) — endpoint `https://storefront-api.fbits.net/graphql`, header `TCS-Access-Token`
- [cdn.jsdelivr.net/gh/deco-cx/apps — wake/mod.ts](https://cdn.jsdelivr.net/gh/deco-cx/apps@0.63.0/wake/mod.ts) — confirmação do header `TCS-Access-Token` e endpoint no código de integração de terceiros

### Terciárias (confiança LOW — marcadas ASSUMED)

- WebSearch confirmando endpoint `storefront-api.fbits.net/graphql` — corrobora as fontes secundárias mas não é fonte independente
- Inferência sobre o formato do prefixo `tcs_loja_xxx` a partir da documentação de CLI local da Wake

---

## Metadados

**Breakdown de confiança:**
- Stack/ambiente: HIGH — pacotes verificados no ambiente Python 3.14.3 real; slopcheck OK em todos
- Estrutura do engine: HIGH — código-fonte do `SFCCEngine`, `ShopifyEngine`, `factory.py`, `models.py`, `BaseEngine` lidos diretamente
- API GraphQL Wake (endpoint + query `search` + campos `productName`/`prices.price`): MEDIUM — documentação oficial Wake verificada via WebFetch
- Auto-extração do token (localização no HTML): MEDIUM — documentação do Storefront SDK verificada via WebFetch; A1-A6 ainda como ASSUMED
- Spike (confirmação empírica fim-a-fim): LOW até o GO do Wave 0 — é a razão de existir o spike

**Data da pesquisa:** 2026-06-24
**Válido até:** 2026-07-24 (30 dias para documentação estável; a parte empírica é confirmada pelo spike Wave 0 nesta própria phase)
