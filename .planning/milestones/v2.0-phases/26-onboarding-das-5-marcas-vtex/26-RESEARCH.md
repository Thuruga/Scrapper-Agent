# Phase 26: Onboarding das 5 Marcas VTEX - Research

**Researched:** 2026-06-19
**Domain:** Brand onboarding — seed script, engine detection, category mapping, dual persistence
**Confidence:** HIGH (all cited code paths verified against current source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Domínios e `brand_key` fornecidos pelo usuário — descoberta de storefronts pulada.
  | `brand_key`  | `brand_name`   | `domain`                    |
  |---|---|---|
  | `levis`       | Levi's         | `www.levi.com.br`           |
  | `calvinklein` | Calvin Klein   | `www.calvinklein.com.br`    |
  | `zapalla`     | Zapalla        | `www.zapalla.com.br`        |
  | `austral`     | Austral        | `secure.austral.com.br` ⚠️ |
  | `trackfield`  | Track & Field  | `www.tf.com.br`             |

- **D-02:** `secure.austral.com.br` é atípico — se redirecionar, `detect_engine` (com `allow_redirects=False`) falha silenciosamente → retorna `"unknown"` → marca fica inativa. Investigar variações (`www.austral.com.br`) antes de persistir.
- **D-03:** Mapear subset núcleo comparável (apenas categorias que a marca realmente tem via `discover_categories`). Não mapear o catálogo inteiro.
- **D-04:** Ancorar nos slugs canônicos de `_RAW_CATEGORIES`: `camisas`, `polos`, `camisetas`, `calcas`, `bermudas`, `jaquetas`. NÃO criar taxonomia livre.
- **D-05:** Critérios de sucesso passam só com registro + busca verificada; mappings são entregues para preparar Phase 29/monitoramento.
- **D-06:** Script seed idempotente — re-executável sem duplicar.
- **D-07:** Mappings gravados em `DynamicBrand.mappings` (data-driven como `bck`). NÃO editar `services/category_mapping.py`.
- **D-08:** Persistência dual dev/prod é invariante: `engine`, `is_active` e `mappings` devem cair em Supabase (prod) e `brands.json` (dev).
- **D-09:** Auto-match por nome + revisão humana antes de persistir — o script imprime o de/para proposto e aguarda confirmação.
- **D-10:** Verificação em duas camadas: (a) smoke ao vivo — 1 query por marca; (b) teste offline/determinístico de contrato (sem rede).
- **D-11:** `"unknown"` NÃO é estado final aceitável — investigar + re-tentar. Override manual para `"vtex"` foi rejeitado (viola critério 2).

### Claude's Discretion

- Forma exata do auto-match de nomes (normalização: lowercase, sem acento, singular/plural).
- Nome/localização do script seed (ex.: `scripts/onboard_vtex_brands.py`) e modo de invocação.
- Termo de query do smoke por marca (ex.: termo genérico de moda masculina).

### Deferred Ideas (OUT OF SCOPE)

- Engines Wake (Richards), SFCC (Lacoste, Hugo Boss), Inditex (Zara).
- Mapeamento completo de catálogo.
- Diagnóstico de saúde de categorias (Phase 29, DIAG-01/02).
- UI de gestão de marcas (Phase 27, MGMT-02).
- Frete via checkout (Phase 30, FRET-05).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-01 | Usuário pode adicionar e buscar/monitorar as 5 marcas concorrentes VTEX com engine reconfirmada via `detect_engine` no momento da adição. | Caminho completo verificado: `create_brand(engine="auto")` → `detect_engine` → `add_brand` → `set_active(False)` se "unknown". `discover_categories` + `update_mappings` também verificados. Tudo via service layer existente, zero código novo de regra de negócio. |
</phase_requirements>

---

## Summary

Esta phase onboarda as 5 marcas VTEX concorrentes via script seed. O caminho técnico completo já existe desde a Phase 25: `create_brand(engine="auto")` reconfirma a engine via `detect_engine`; `GET /brands/{key}/discover` lista a árvore VTEX; `PUT /brands/{key}/mappings` persiste o de/para. O script orquestra esses três passos sem inventar fluxo novo.

**Todos os code paths citados no CONTEXT.md foram verificados contra o código atual e estão corretos** — funções e assinaturas batem. Há uma diferença importante a reportar: `add_brand` no modo "upsert" (marca já existente) atualiza apenas `domain` e `brand_name`, mas NÃO atualiza `engine` nem `is_active`. Isso cria um landmine de idempotência: se o script for re-executado em cima de uma marca que foi salva como `"unknown"`, a engine antiga persiste. O script precisa forçar a atualização de `engine` e `is_active` explicitamente via `set_active` após o `add_brand`.

O único risco técnico real é o domínio `secure.austral.com.br` — `detect_engine` usa `allow_redirects=False` no step 3 (HTML fallback), o que significa que se o host redirecionar o código obtém apenas os headers de redirect sem HTML, o HTML estará vazio, e o resultado será `"unknown"`. O plano precisa incluir um passo de investigação desse domínio antes de persistir.

**Primary recommendation:** O script seed deve chamar `create_brand(engine="auto")` para reconfirmação, verificar que o resultado tem `engine="vtex"` (não `"unknown"`), e só então chamar `discover_categories` + `update_mappings`. Para Austral, incluir retry com `www.austral.com.br` antes de desistir.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reconfirmação de engine | API layer (`detect_engine`) | — | Função já existe em `api/routes_brands.py`; lógica de probe HTTP encapsulada ali |
| Persistência de marca | Service layer (`brand_service`) | Backend (Supabase/JSON) | `_save` abstrai o backend; `add_brand`, `set_active`, `update_mappings` são a API pública |
| Descoberta de categorias | Engine layer (`VTEXEngine.discover_categories`) | API layer (`GET /brands/{key}/discover`) | Lógica VTEX no engine; rota é thin wrapper |
| Auto-match de nomes | Script seed | — | Lógica de normalização/matching fica no script; saída é revisada pelo operador antes de persistir |
| Persistência de mappings | Service layer (`update_mappings`) | — | `update_mappings` já salva via `_save` dual |
| Verificação de contrato (D-10b) | Test layer (`tests/`) | — | Offline/determinístico, sem rede, padrão estabelecido do projeto |

---

## Standard Stack

Esta phase não instala novos pacotes — usa exclusivamente o stack existente.

### Core (já instalado)

| Componente | Onde vive | Propósito nesta phase |
|------------|-----------|----------------------|
| `api/routes_brands.py:detect_engine` | API layer | Reconfirma engine do domínio via HTTP probes |
| `services/brand_service.py:BrandManagerService` | Service layer | `add_brand`, `set_active`, `update_mappings`, `_save` |
| `services/engines/vtex_engine.py:VTEXEngine.discover_categories` | Engine layer | Descobre árvore de categorias VTEX via `VtexApiClient.fetch_categories` |
| `services/engines/factory.py:EngineFactory.get_engine` | Factory | Resolve engine por `brand_key` |
| `core/models.py:DynamicBrand / DynamicBrandCreate / CategoryMapping` | Models | Contratos de dados |
| `data/brands.json` | Dev persistence | Backend local; Supabase é o backend de produção |

### No New Packages

Nenhum pacote externo é adicionado. O script seed usa apenas `asyncio`, `json`, a service layer existente, e opcionalmente `unicodedata` (stdlib) para normalização de acentos no auto-match.

---

## Package Legitimacy Audit

Não aplicável — esta phase não instala nenhum pacote externo.

---

## Architecture Patterns

### System Architecture Diagram

```
Script seed (scripts/onboard_vtex_brands.py)
    │
    ├─→ Para cada marca em BRAND_TABLE:
    │       │
    │       ├─→ [1] create_brand(DynamicBrandCreate(engine="auto"))
    │       │       │
    │       │       ├─→ detect_engine(domain)
    │       │       │       ├─→ Probe Shopify (collections.json)
    │       │       │       ├─→ Probe VTEX (category/tree/1)
    │       │       │       └─→ Probe HTML (allow_redirects=False)
    │       │       │               ├─→ Wake marker → "unknown"
    │       │       │               ├─→ VTEX marker → "vtex"
    │       │       │               └─→ nenhum → "unknown"
    │       │       │
    │       │       ├─→ brand_service.add_brand(data)
    │       │       └─→ if engine=="unknown": brand_service.set_active(key, False)
    │       │
    │       ├─→ Verificar resultado.engine == "vtex"
    │       │       └─→ se "unknown": PARAR, investigar domínio (D-11), retry
    │       │
    │       ├─→ [2] VTEXEngine.discover_categories()
    │       │       └─→ VtexApiClient.fetch_categories(domain)
    │       │               ├─→ Tenta domínio direto /api/catalog_system/pub/category/tree/3
    │       │               ├─→ Auto-Discovery: extrai account name do HTML
    │       │               └─→ Fallback: {account}.vtexcommercestable.com.br
    │       │                   → _flatten_vtex_tree → [{name, path (URL)}]
    │       │
    │       ├─→ [3] Auto-match: normalizar names → casar com slugs canônicos
    │       │       └─→ Imprimir de/para proposto → aguardar confirmação operador
    │       │
    │       └─→ [4] brand_service.update_mappings(key, [CategoryMapping(...)])
    │               └─→ _save → Supabase (prod) ou brands.json (dev)
    │
    └─→ Smoke: engine_factory.search_all_brands(query) → verificar ≥1 produto por marca
```

### Recommended Project Structure

```
scripts/
└── onboard_vtex_brands.py    # Script seed idempotente (novo)

tests/
└── test_brand_contract.py    # Teste de contrato offline D-10b (novo)
```

Nenhuma alteração em `api/`, `services/`, ou `core/` é necessária.

### Pattern 1: Script Seed Idempotente

**What:** Script que pode ser re-executado sem duplicar marcas nem sobrescrever mappings já corretos.

**When to use:** Onboarding inicial e re-execução após correção de domínio (ex.: Austral).

**Landmine de idempotência — CRÍTICO:** `add_brand` no modo upsert (marca já existe) atualiza apenas `domain` e `brand_name`. Ele NÃO atualiza `engine` nem `is_active`. Portanto:

```python
# Source: services/brand_service.py:188-198 (verificado)
def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
    key = data.brand_key.lower().strip()
    if key in self.brands:
        self.brands[key].domain = data.domain       # apenas domain...
        self.brands[key].brand_name = data.brand_name  # ...e brand_name
        # engine e is_active NÃO são atualizados no upsert!
    else:
        new_brand = DynamicBrand(**data.model_dump())
        self.brands[key] = new_brand
    self._save(self.brands[key])
    return self.brands[key]
```

**Consequência:** Se o script for re-executado em cima de uma marca salva com `engine="unknown"` (de uma tentativa anterior), o `add_brand` não corrige a engine — retorna o objeto antigo. O script DEVE verificar `result.engine` após `add_brand` e, se necessário, forçar `brand_service.brands[key].engine = detected_engine` + `_save` diretamente, OU deletar e recriar.

**Estratégia recomendada de idempotência:**

```python
# Pseudocódigo do padrão correto
async def onboard_brand(brand_key, brand_name, domain):
    data = DynamicBrandCreate(
        brand_key=brand_key,
        brand_name=brand_name,
        domain=domain,
        engine="auto"  # detect_engine é chamado dentro de create_brand
    )
    # create_brand já chama detect_engine e set_active(False) se "unknown"
    result = await create_brand(data)  # ou chamar brand_service diretamente

    if result.engine != "vtex":
        print(f"[WARN] {brand_key}: engine={result.engine!r} — investigar domínio")
        return None  # não prosseguir com discover/mappings

    # Re-executável: se mappings já existem, perguntar ao operador se quer sobrescrever
    if result.mappings:
        print(f"[SKIP] {brand_key}: mappings já existem ({len(result.mappings)} itens)")
        return result

    return result
```

### Pattern 2: CategoryMapping — Shape Exato

**What:** Campos obrigatórios do modelo `CategoryMapping` para a serialização correta via `update_mappings`.

```python
# Source: core/models.py:199-205 (verificado)
class CategoryMapping(BaseModel):
    canonical_slug: str   # ex: "polos", "camisas" — deve ser um dos slugs de _RAW_CATEGORIES
    vtex_fq_path: str     # ex: "/roupas/polos" ou "C:/480/523/" — o path/fq da categoria no site
    label: str            # ex: "Polos Masculinas" — label display, pode ser livre
```

**Output de `_flatten_vtex_tree`:**

```python
# Source: services/engines/vtex_engine.py:40-53 (verificado)
# Retorna: List[{"name": str, "path": str}]
# onde "path" é a URL completa: ex "https://www.levi.com.br/roupas/masculino/jeans"
# NÃO é apenas o path relativo — é a URL inteira extraída do campo "url" dos nós VTEX
```

**Atenção ao `vtex_fq_path` para marcas VTEX dinâmicas:** O campo `vtex_fq_path` de `CategoryMapping` é usado por `resolve_category_for_brands` (linha 228) como path para construir a URL de categoria scan. Para marcas VTEX dinâmicas, esse campo deve ser o **path relativo** (ex: `/roupas/jeans`), não o FQ (`C:/...`), porque o código em `resolve_category_for_brands:229-233` verifica `if not path.startswith("/")` e não consegue gerar a URL do category scan a partir de um FQ.

```python
# Source: services/category_mapping.py:228-239 (verificado)
path = dynamic_mapping.vtex_fq_path
if not path.startswith("/"):
    # Se for um FQ (C:/...), não conseguimos gerar a URL da categoria diretamente
    pass  # sem erro, mas url gerada ficará errada
result[bk_lower] = {
    "url": f"https://{domain}{path if path.startswith('/') else '/' + path}",
    ...
}
```

**Conclusão:** Para marcas VTEX dinâmicas (as 5 desta phase), `vtex_fq_path` deve guardar o **path relativo da URL** (ex: `/roupas/jeans`), que é o que `_flatten_vtex_tree` retorna em `path` (como URL completa — o script precisa extrair o path relativo dela). O nome do campo `vtex_fq_path` é enganoso para VTEX dinâmica.

### Pattern 3: Auto-Match de Nomes

**What:** Normalização para casar nomes de categorias descobertas com slugs canônicos.

```python
# Slugs canônicos (source: services/category_mapping.py:_RAW_CATEGORIES, verificado)
CANONICAL_SLUGS = {
    "camisas": ["camisa", "camisas"],
    "polos":   ["polo", "polos"],
    "camisetas": ["camiseta", "camisetas", "t-shirt", "tshirt"],
    "calcas":  ["calca", "calcas", "calças", "calça", "jeans", "denim"],
    "bermudas": ["bermuda", "bermudas", "short", "shorts"],
    "jaquetas": ["jaqueta", "jaquetas", "casaco", "casacos", "blusa"],
    "infantil": ["infantil", "kids", "mini"],
}

import unicodedata

def normalize(text: str) -> str:
    """Lowercase + remove acentos."""
    text = text.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
```

### Anti-Patterns to Avoid

- **Hardcodar engine="vtex" sem detect_engine:** Viola critério 2 ("reconfirmado por `detect_engine`, não assumido manualmente"). D-11 rejeitou override manual explicitamente.
- **Editar `_RAW_CATEGORIES` em `category_mapping.py`:** D-07 rejeitou isso. Mappings dinâmicos vão em `DynamicBrand.mappings`, não no código hardcoded.
- **Assumir que `add_brand` idempotente atualiza engine:** NÃO atualiza. Ver landmine documentado em Pattern 1.
- **Usar `vtex_fq_path` para armazenar FQ (`C:/...`) em marcas dinâmicas:** `resolve_category_for_brands` não consegue gerar URL de scan a partir de FQ. Usar path relativo.
- **Mapear `factory.get_engine` por `brand_key` antes do `add_brand`:** `get_engine` busca `brand_data` no `brand_service`; se a marca não existir ainda, cai em `VTEXEngine` por default — mas `discover_categories` falhará ao tentar `get_brand`. Sempre chamar `add_brand` primeiro.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detectar engine VTEX | Probe HTTP custom | `detect_engine` em `api/routes_brands.py` | Já implementa 6 steps incluindo Wake, com `allow_redirects=False` |
| Descobrir categorias VTEX | Parser HTML custom | `VTEXEngine.discover_categories()` + `VtexApiClient.fetch_categories` | Já implementa Auto-Discovery de account name + fallback vtexcommercestable.com.br |
| Persistência dual | Lógica de if/else Supabase vs JSON | `brand_service._save(brand)` | Abstrai o backend transparentemente |
| Persitir marca | Inserção direta em JSON | `brand_service.add_brand(DynamicBrandCreate)` | Valida schema Pydantic, garante lowercase do key |
| Persitir mappings | Editar JSON diretamente | `brand_service.update_mappings(key, [CategoryMapping])` | Persiste via `_save` com upsert Supabase correto |
| Aplainar árvore VTEX | Recursão custom | `VTEXEngine._flatten_vtex_tree(raw_tree)` | Já existe e testado |

**Key insight:** O script seed é um orquestrador de chamadas a código existente — não deve conter lógica de negócio nova exceto o auto-match de nomes (D-09).

---

## Verified Code Path Audit

**RESULTADO: TODOS OS CODE PATHS CITADOS NO CONTEXT.md EXISTEM E AS ASSINATURAS BATEM.**

| Code path citado | Status | Observação |
|---|---|---|
| `api/routes_brands.py:detect_engine` (L14-69) | VERIFIED | Existe L14-69. `allow_redirects=False` está em L44. |
| `create_brand` (engine="auto" → detect; "unknown" → inactive) | VERIFIED | L72-94. Lógica D-04 está implementada. |
| `GET /brands/{key}/discover` | VERIFIED | L134-153. Thin wrapper sobre `engine.discover_categories()`. |
| `PUT /brands/{key}/mappings` | VERIFIED | L165-173. Delega para `brand_service.update_mappings`. |
| `brand_service.add_brand` | VERIFIED | L188-198. Upsert parcial (landmine documentado). |
| `brand_service.set_active` | VERIFIED | L218-224. Implementado e testado (Phase 25). |
| `brand_service.update_mappings` | VERIFIED | L226-232. |
| `brand_service._save` / `_upsert_to_supabase` / `_save_to_json` | VERIFIED | L180-186 / L154-164 / L74-83. |
| `category_mapping.py:_RAW_CATEGORIES` slugs canônicos | VERIFIED | L45-118. Slugs: `camisas, polos, camisetas, calcas, bermudas, jaquetas, infantil`. |
| `resolve_category_for_brands` (hardcoded → dinâmico) | VERIFIED | L191-250. Fallback dinâmico em L223-239. |
| `get_canonical_categories` (hardcoded + dinâmico) | VERIFIED | L143-188. Adiciona grupo "Custom" para slugs novos. |
| `VTEXEngine.discover_categories` | VERIFIED | L20-53. Chama `VtexApiClient.fetch_categories(domain)` → `_flatten_vtex_tree`. |
| `_flatten_vtex_tree` retorna `[{name, path}]` | VERIFIED | L40-53. `path` = URL completa extraída de `node["url"]`. |
| `VTEXEngine.search` NÃO usa mappings | VERIFIED | L62-84. Delega para `VtexApiClient.search(query=...)`. |
| `factory.get_engine` resolve por campo `engine` | VERIFIED | L16-45. Default "vtex" se brand_data não encontrado. |
| `factory.search_all_brands(active_only=True)` | VERIFIED | L47-92. L70: `list_brands(active_only=True)`. |
| `DynamicBrand / DynamicBrandCreate / CategoryMapping` shapes | VERIFIED | `core/models.py:199-233`. |
| `data/brands.json` formato | VERIFIED | `bck` tem mappings dinâmicos com `canonical_slug/vtex_fq_path/label`. |

**Diferença não-trivial encontrada (landmine):** `add_brand` no modo upsert NÃO atualiza `engine` nem `is_active`. Documentado em Pattern 1 e Common Pitfalls.

**Diferença na numeração de linhas:** CONTEXT.md cita `create_brand` em L72-94 (matches); `list_brands/GET /brands/` em L72 (CONTEXT.md de Phase 25 — o número delas mudou para L97-131 após Phase 25 adicionou `PATCH /brands/{key}/active`). Não impacta funcionalidade.

---

## Austral Domain Risk (D-02) — Análise Detalhada

`detect_engine` aplica `allow_redirects=False` **somente no step 3** (HTML fallback, L44). Os steps 1 e 2 (Shopify + VTEX API) usam a sessão aiohttp sem `allow_redirects=False` explícito — portanto seguem redirects.

**Fluxo para `secure.austral.com.br`:**

1. **Step 1 (Shopify probe):** GET `https://secure.austral.com.br/collections.json` — provavelmente 404 ou redirect para domínio de checkout, mas aiohttp segue o redirect; o JSON de checkout não terá `"collections"` → não detecta Shopify.
2. **Step 2 (VTEX API probe):** GET `https://secure.austral.com.br/api/catalog_system/pub/category/tree/1` — se o host for de checkout, provavelmente 404 ou redirect para login; não retorna 200 → não detecta VTEX.
3. **Step 3 (HTML probe, `allow_redirects=False`):** GET `https://secure.austral.com.br/` com `allow_redirects=False` — se o host emite redirect (301/302), a sessão para imediatamente. `resp.text()` retorna o body do response de redirect, que é tipicamente um HTML mínimo de redirect sem marcadores de plataforma → `html_lower` não contém `fbitsstatic.net`, `vtexassets.com`, `vtexcommercestable.com`, `cdn.shopify.com` → cai no Step 6 → retorna `"unknown"`.

**Conclusão:** Se `secure.austral.com.br` redirecionar (e subdomínios `secure.` quase sempre redirecionam), `detect_engine` retorna `"unknown"` e a marca fica inativa. O plano DEVE incluir:
1. Tentar `www.austral.com.br` primeiro.
2. Se `www.austral.com.br` também falhar, tentar `austral.com.br`.
3. Somente se nenhuma variação detectar `"vtex"`, sinalizar para investigação manual.

---

## Idempotência e Dual Persistence (D-06/D-08) — Análise

### add_brand: comportamento de upsert

```
brand_key já existe → atualiza domain + brand_name, NÃO engine/is_active/mappings
brand_key não existe → cria DynamicBrand(**data.model_dump()) com todos os campos
```

**Implicação para re-execução:**

- Primeira execução: cria com `engine="vtex"` (após detect), `is_active=True`, `mappings=[]`.
- Segunda execução: `add_brand` retorna a brand existente sem alterar `engine` — CORRETO se engine já era `"vtex"`.
- Segunda execução após falha de Austral: brand tinha `engine="unknown"`, `is_active=False` → `add_brand` retorna objeto com `engine="unknown"` → script detecta `!= "vtex"` → re-tenta domínio correto → chama `detect_engine` com novo domínio → usa `save_brand` ou `_save` diretamente para corrigir a engine.

**Dual persistence:** `_save(brand)` chama `_upsert_to_supabase(brand)` se `SUPABASE_URL` + `SUPABASE_KEY` presentes, ou `_save_to_json()` (grava todo o dict) caso contrário. Ambos os caminhos persistem o objeto `DynamicBrand` completo incluindo `engine`, `is_active` e `mappings`. Invariante satisfeita.

**Atenção no `_save_to_json`:** Salva **todas** as marcas em `brands.json` a cada chamada (`model_dump()` de todo o dict). Se `is_active` ou `engine` foram mutados in-place no dict `self.brands`, a serialização pegará o estado mais recente.

---

## Common Pitfalls

### Pitfall 1: Domínio `secure.austral.com.br` retorna `"unknown"` silenciosamente

**What goes wrong:** `detect_engine` com `allow_redirects=False` no step 3 não lê HTML real de hosts que redirecionam. Retorna `"unknown"`, `set_active(False)` é chamado, script prossegue sem avisar que a brand ficou inativa.

**Why it happens:** `secure.` é convencionalmente o subdomínio de checkout VTEX, que redireciona para o domínio principal. `allow_redirects=False` é uma decisão de segurança (T-25-01-SR) que tem o efeito colateral de tornar a detecção cega a redirects.

**How to avoid:** Verificar `result.engine == "vtex"` após cada `create_brand`. Se `"unknown"`, não prosseguir e tentar variações de domínio.

**Warning signs:** Brand salva com `is_active=False` logo após o `add_brand`.

### Pitfall 2: `add_brand` não atualiza `engine` no upsert

**What goes wrong:** Segunda execução do script não corrige uma engine errada de execução anterior — retorna o objeto antigo com `engine="unknown"`.

**Why it happens:** Comportamento intencional do upsert (`add_brand` L190-192): apenas domain/brand_name são atualizados para evitar sobrescrever mappings/is_active acidentalmente.

**How to avoid:** Após `add_brand`, verificar `result.engine`. Se diferente do detectado, corrigir manualmente via `brand_service.brands[key].engine = detected_engine` + `brand_service._save(brand_service.brands[key])`.

**Warning signs:** Script re-executado → brand aparece como inativa apesar de domínio correto.

### Pitfall 3: `vtex_fq_path` com FQ em vez de path relativo quebra category scan

**What goes wrong:** Salvar `vtex_fq_path = "C:/1/2/"` (VTEX FQ) em vez do path relativo `/roupas/calcas` faz `resolve_category_for_brands` gerar URL errada como `https://domain/C:/1/2/` em vez de `https://domain/roupas/calcas`.

**Why it happens:** O campo se chama `vtex_fq_path` mas para marcas VTEX dinâmicas o código em `category_mapping.py:229` espera um path relativo começando com `/`.

**How to avoid:** `_flatten_vtex_tree` retorna `path` como **URL completa** (ex: `https://www.levi.com.br/roupas/jeans`). O script deve extrair o **path relativo** usando `urlparse(url).path`. Exemplo: `from urllib.parse import urlparse; path = urlparse(discovered_item["path"]).path`.

**Warning signs:** Category scan para marca dinâmica gera URL `https://domain/C:/...`.

### Pitfall 4: `engine_factory.get_engine` antes do `add_brand`

**What goes wrong:** `get_engine` chama `brand_service.get_brand(brand_key)` — retorna None se a marca não existir ainda → cai em `VTEXEngine(brand_key)` por default → `discover_categories` chama `brand_service.get_brand` de novo → retorna None → `discover_categories` retorna `[]` silenciosamente.

**Why it happens:** `get_engine` tem default para VTEX mesmo sem brand registrada, mas `VTEXEngine.discover_categories` depende de `brand_service.get_brand` para obter o domínio.

**How to avoid:** Sempre chamar `add_brand` antes de `discover_categories`. Verificar que `brand_service.get_brand(key)` não é None antes de chamar `discover_categories`.

### Pitfall 5: `VtexApiClient.fetch_categories` com URL completa vs path

**What goes wrong:** `_flatten_vtex_tree` retorna itens com `path` = URL completa (ex: `https://www.levi.com.br/roupas/jeans`). Se o script usar diretamente como `vtex_fq_path`, a URL de category scan ficará duplicada.

**Why it happens:** `_flatten_vtex_tree` extrai `url` do nó VTEX, que é uma URL completa, não apenas o path.

**How to avoid:** Extrair path relativo: `from urllib.parse import urlparse; path = urlparse(item["path"]).path`.

---

## Verification Approach (D-10) — Teste de Contrato Offline

### Padrão estabelecido pelo projeto

O projeto usa classe de teste sem pytest-asyncio — asyncio.run() para funções async (ver `test_engine_detection.py`, `test_brand_active.py`, `test_cross_marketplace_service.py`).

Padrão de mock de serviço em memória (de `test_brand_active.py`):

```python
# Source: tests/test_brand_active.py:31-57 (verificado)
def _make_service_with_brands():
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    svc._check_reload = unittest.mock.MagicMock()  # sem I/O
    # popular svc.brands diretamente
    return svc
```

### Contrato a testar (D-10b)

Um teste de contrato offline para Phase 26 deve verificar, sem rede:

1. Brand registrada tem `engine="vtex"` (não `"unknown"`).
2. Brand registrada tem `is_active=True`.
3. `brand_service.get_brand(key).mappings` não está vazio após `update_mappings`.
4. Cada mapping tem `canonical_slug` pertencente aos slugs canônicos de `_RAW_CATEGORIES`.
5. Brand aparece em `list_brands(active_only=True)`.
6. `resolve_category_for_brands(slug, [brand_key])` retorna URL válida para pelo menos um slug mapeado.

**Arquivo sugerido:** `tests/test_vtex_brand_onboarding_contract.py`

**Importante:** Mockar `_save` para evitar I/O, e mockar `detect_engine` para retornar `"vtex"` — o objetivo é testar o estado final, não o probe de rede.

---

## Runtime State Inventory

Esta phase é de onboarding (não rename/refactor), mas há estado que o script seed cria e que persiste:

| Category | Items | Action Required |
|----------|-------|------------------|
| Stored data | `brands.json` — 5 novas entradas após onboarding | Script seed cria; idempotente via `add_brand` |
| Stored data | Supabase `brands` table — 5 novas rows em prod | `_upsert_to_supabase` cria/atualiza; idempotente via upsert |
| Live service config | Nenhum serviço externo configurado para as 5 marcas | N/A |
| OS-registered state | Nenhum (não há Task Scheduler, pm2, etc. para brands) | N/A |
| Secrets/env vars | Nenhum novo secret necessário — usa `SUPABASE_URL`/`SUPABASE_KEY` existentes | N/A |
| Build artifacts | Nenhum | N/A |

**Nada além de `brands.json` e Supabase é afetado.**

---

## Environment Availability

| Dependency | Required By | Available | Fallback |
|------------|------------|-----------|----------|
| Python (asyncio, unicodedata) | Script seed | Stdlib — sempre disponível | N/A |
| `SUPABASE_URL` + `SUPABASE_KEY` | Persistência prod | Variável de ambiente — não verificável offline | `brands.json` (dev mode) |
| Rede para `detect_engine` | Reconfirmação de engine | Necessária na execução | Re-executar quando disponível |
| Rede para `discover_categories` | Descoberta de categorias | Necessária na execução | Re-executar quando disponível |
| Rede para smoke (D-10a) | Critério 1 (busca retorna produtos) | Necessária na execução | Smoke é manual/ao-vivo — não automatizado |

**Missing dependencies with no fallback:**
- Rede externa durante execução do script (detect_engine + discover_categories + smoke). O script não pode ser executado offline.

**Missing dependencies with fallback:**
- Supabase: se não configurado, persiste em `brands.json` (dev mode). Comportamento correto para ambiente de desenvolvimento.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (sem configuração especial — sem pytest.ini/pyproject.toml de teste) |
| Config file | none — pytest coleta `tests/` por default |
| Quick run command | `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-01 | Brand registrada com engine="vtex" | unit (contrato offline) | `pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_engine_is_vtex -x` | ❌ Wave 0 |
| COMP-01 | Brand registrada com is_active=True | unit (contrato offline) | `pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_brand_is_active -x` | ❌ Wave 0 |
| COMP-01 | Mappings persistidos e com canonical_slug válido | unit (contrato offline) | `pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_mappings_persisted -x` | ❌ Wave 0 |
| COMP-01 | Brand aparece em list_brands(active_only=True) | unit (contrato offline) | `pytest tests/test_vtex_brand_onboarding_contract.py::TestBrandContract::test_brand_in_active_list -x` | ❌ Wave 0 |
| COMP-01 | Busca retorna produtos reais (critério 1) | smoke ao vivo (manual) | (manual — WAF/rede) | N/A (manual) |
| COMP-01 | engine="unknown" brands ficam inativas | unit (já existente) | `pytest tests/test_engine_detection.py::TestCreateBrandUnknown -x` | ✅ |

### Sampling Rate

- **Por task commit:** `python -m pytest tests/test_vtex_brand_onboarding_contract.py -q`
- **Por wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Suite completa verde antes de `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_vtex_brand_onboarding_contract.py` — cobre COMP-01 (brand contract offline)

*(Infraestrutura de testes existente cobre COMP-01 parcialmente via `test_engine_detection.py` — mas contrato de onboarding completo precisa de arquivo novo.)*

---

## Security Domain

Esta phase não introduz novos endpoints de autenticação, sessão ou criptografia. O risco principal é injeção de dados inválidos via `DynamicBrandCreate`.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — script seed é operação administrativa local |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Já coberto por API key existente |
| V5 Input Validation | yes | `DynamicBrandCreate` com Pydantic (field_validator `clean_domain` sanitiza scheme/trailing slash) |
| V6 Cryptography | no | N/A |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Domain com scheme injetado (ex: `http://evil.com`) | Tampering | `DynamicBrandCreate.clean_domain` remove `https://`, `http://`, strips `/` — verificado em `models.py:214-218` |
| Script seed executado com `brand_key` arbitrário | Tampering | `add_brand` normaliza para lowercase; Pydantic valida tipos |
| `vtex_fq_path` com path traversal (ex: `/../../../etc`) | Tampering | Não há validação de path no modelo — risco baixo (dado interno, não exposto externamente) |

---

## Open Questions

1. **Domínio real da Austral**
   - What we know: `secure.austral.com.br` provavelmente redireciona para domínio principal; `detect_engine` com `allow_redirects=False` retornará `"unknown"`.
   - What's unclear: Qual é o domínio real do storefront VTEX da Austral? `www.austral.com.br`? `austral.com.br`?
   - Recommendation: O script deve testar `www.austral.com.br` primeiro (step de D-11), imprimir o resultado, e aguardar confirmação antes de persistir o domínio.

2. **Categorias disponíveis por marca**
   - What we know: Levi's é especializada em jeans/denim; pode não ter todas as categorias canônicas (`polos`, `jaquetas`). Track & Field tem foco em sportswear — `camisas` formais podem não existir.
   - What's unclear: Quais dos 6 slugs canônicos existem em cada uma das 5 marcas.
   - Recommendation: `discover_categories` resolve isso ao vivo. O auto-match deve mostrar claramente quais slugs ficaram sem correspondência por marca.

3. **`bck` é Shopify, não VTEX — o pattern de mappings é transferível?**
   - What we know: `bck` usa `vtex_fq_path` para paths Shopify (ex: `/collections/calcas`). Para marcas VTEX, `vtex_fq_path` deve ser o path relativo do site VTEX.
   - What's unclear: O code path de `resolve_category_for_brands` trata marcas VTEX dinâmicas da mesma forma que Shopify? SIM — o código em L228 não discrimina por engine, usa `vtex_fq_path` como path para construir URL.
   - Recommendation: Padrão é transferível. Usar path relativo (não FQ) em `vtex_fq_path` para todas as 5 marcas.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `secure.austral.com.br` redireciona para um domínio principal | Pitfall 1, Austral Domain Risk | Se não redirecionar e servir VTEX diretamente, detect_engine pode funcionar — risco baixo |
| A2 | `www.austral.com.br` é o domínio correto do storefront VTEX da Austral | Open Questions | Se o storefront estiver em outro domínio, detect_engine retorna "unknown" para todas as variações |
| A3 | As 5 marcas (levis, calvinklein, zapalla, trackfield) respondem corretamente à API VTEX catalog_system/pub/category/tree | Standard Stack | Se alguma estiver atrás de FastStore sem a API padrão, fetch_categories usa auto-discovery e fallback vtexcommercestable.com.br |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `detect_engine` retornava "vtex" como fallback incondicional | Retorna "unknown" + probe Wake (fbitsstatic.net) | Phase 25 | Marcas não-VTEX não entram mais na busca silenciosamente |
| `list_brands` sem filtragem | `list_brands(active_only=True)` no chokepoint | Phase 25 | Marcas inativas excluídas de busca/scheduler/monitor |
| Sem `set_active` | `set_active(key, bool)` implementado + `PATCH /brands/{key}/active` | Phase 25 | Ativação/desativação idempotente |

---

## Sources

### Primary (HIGH confidence — verificado no código fonte)

- `api/routes_brands.py` — funções `detect_engine` (L14-69), `create_brand` (L72-94), `discover_categories` (L134-153), `update_brand_mappings` (L165-173) — lidas e verificadas nesta sessão
- `services/brand_service.py` — `add_brand` (L188-198), `set_active` (L218-224), `update_mappings` (L226-232), `_save` (L180-186), `_upsert_to_supabase` (L154-164), `_save_to_json` (L74-83) — lidas e verificadas nesta sessão
- `services/category_mapping.py` — `_RAW_CATEGORIES` (L45-118), `get_canonical_categories` (L143-188), `resolve_category_for_brands` (L191-250) — lidas e verificadas nesta sessão
- `services/engines/vtex_engine.py` — `discover_categories` (L20-53), `_flatten_vtex_tree` (L40-53), `search` (L62-84) — lidas e verificadas nesta sessão
- `services/engines/factory.py` — `get_engine` (L16-45), `search_all_brands` (L47-92) — lidas e verificadas nesta sessão
- `core/models.py` — `CategoryMapping` (L199-205), `DynamicBrandCreate` (L207-225), `DynamicBrand` (L228-233) — lidas e verificadas nesta sessão
- `data/brands.json` — formato de referência com `bck` como exemplo de mappings dinâmicos — lido nesta sessão
- `tests/test_engine_detection.py`, `tests/test_brand_active.py` — padrão de teste do projeto — lidos nesta sessão
- Suite de testes Phase 25: `python -m pytest tests/test_engine_detection.py tests/test_brand_active.py -q` → **12 passed** (verificado nesta sessão)

### Secondary (MEDIUM confidence)

- `.planning/phases/25-funda-o-de-motores/25-CONTEXT.md` — decisões D-01..D-08 que Phase 25 implementou
- `.planning/phases/26-onboarding-das-5-marcas-vtex/26-CONTEXT.md` — decisões D-01..D-11 para esta phase

---

## Metadata

**Confidence breakdown:**

- Code path audit: HIGH — todos os arquivos lidos e assinaturas verificadas contra o código atual
- Idempotência landmine: HIGH — comportamento de upsert lido diretamente de `brand_service.add_brand`
- Austral domain risk: HIGH — lógica de `allow_redirects=False` verificada em L44 de `routes_brands.py`; raciocínio sobre redirect é ASSUMED (A1)
- vtex_fq_path shape: HIGH — comportamento de `resolve_category_for_brands` lido em L228-239
- Test patterns: HIGH — lidos de test files existentes e suite rodada com sucesso

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (código estável; nenhum refactor pendente nas áreas afetadas)
