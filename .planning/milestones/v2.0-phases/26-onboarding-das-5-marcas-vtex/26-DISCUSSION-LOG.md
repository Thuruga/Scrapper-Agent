# Phase 26: Onboarding das 5 Marcas VTEX - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 26-onboarding-das-5-marcas-vtex
**Areas discussed:** Domínios + keys, Profundidade do mapeamento, Mecanismo & persistência, Definição de pronto + falha

---

## Domínios + keys das marcas

| Option | Description | Selected |
|--------|-------------|----------|
| Eu forneço agora | Usuário cola domínios/keys; researcher pula descoberta | ✓ |
| Researcher descobre | Researcher localiza storefronts BR; usuário confirma depois | |
| Mix | Usuário fornece os que conhece; researcher completa | |

**User's choice:** Eu forneço agora.
**Notes:** Domínios fornecidos — `levis`/www.levi.com.br, `calvinklein`/www.calvinklein.com.br, `zapalla`/www.zapalla.com.br, `austral`/secure.austral.com.br, `trackfield`/www.tf.com.br. Flag levantado por Claude: `secure.austral.com.br` é subdomínio atípico (provável checkout) → reconfirmar na execução por causa do `allow_redirects=False` em `detect_engine`.

---

## Profundidade do mapeamento de categorias

| Option | Description | Selected |
|--------|-------------|----------|
| Subset núcleo comparável | Mapear só canônicas que existem de forma comparável entre marcas | ✓ |
| Mapeamento completo | Todas as ~7 canônicas por marca quando existirem | |
| Só registrar (adiar) | Registrar marcas; mappings vazios, depois | |

**User's choice:** Subset núcleo comparável.
**Notes:** Claude expôs a tensão goal ("categorias mapeadas") vs critérios (não testam mappings) e o fato de a busca por query não usar mappings.

### Sub-decisão: como determinar o núcleo por marca

| Option | Description | Selected |
|--------|-------------|----------|
| Ancorar nas canônicas + auto-discovery | Usar taxonomia canônica existente; mapear por marca via discover_categories só o que existe | ✓ |
| Lista fixa mínima obrigatória | Lista curta que todas as 5 devem ter | |
| Auto-discovery livre por marca | Categorias como vierem, sem amarrar ao canônico | |

**User's choice:** Ancorar nas canônicas + auto-discovery.
**Notes:** Preserva "banana com banana" (comparabilidade), o propósito do de/para canônico.

---

## Mecanismo & persistência

| Option | Description | Selected |
|--------|-------------|----------|
| Script seed + DynamicBrand.mappings | Script idempotente: create_brand→discover→grava mappings dinâmicos via brand_service (dev+prod) | ✓ |
| Manual via API + hardcoded no código | POST /brands/ manual + adicionar paths ao _RAW_CATEGORIES | |
| Você decide | Planner escolhe | |

**User's choice:** Script seed + DynamicBrand.mappings.
**Notes:** `resolve_category_for_brands` já consulta mappings dinâmicos; sem tocar category_mapping.py; persistência dual via `_save`.

### Sub-decisão: casamento path → slug

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-match por nome + revisão | Normaliza e casa; imprime de/para; persiste após confirmação | ✓ |
| Totalmente automático | Casa e persiste direto, sem revisão | |
| Seleção manual | Script lista; usuário escolhe cada path→slug | |

**User's choice:** Auto-match por nome + revisão.
**Notes:** Evita gravar path errado silenciosamente em nome ambíguo.

---

## Definição de pronto + falha

| Option | Description | Selected |
|--------|-------------|----------|
| Smoke ao vivo + teste offline de contrato | 1 query/marca ao vivo + teste offline determinístico do contrato | ✓ |
| Só smoke ao vivo manual | 1 query/marca, sem rede de segurança automatizada | |
| Teste automatizado ao vivo por marca | Bate na busca VTEX real; frágil (WAF/geo) | |

**User's choice:** Smoke ao vivo + teste offline de contrato.
**Notes:** Alinhado à filosofia offline/determinística do projeto.

### Sub-decisão: engine ≠ vtex no add-time

| Option | Description | Selected |
|--------|-------------|----------|
| Investigar + re-tentar até reconfirmar | unknown não é final; ajustar domínio e re-rodar até vtex; marca inativa até lá | ✓ |
| Aceitar inativa e seguir | Deixa inativa (D-04) e segue | |
| Override manual para vtex | Força engine=vtex sem reconfirmar | |

**User's choice:** Investigar + re-tentar até reconfirmar.
**Notes:** Override rejeitado por violar critério 2 (reconfirmado, não assumido).

---

## Claude's Discretion

- Normalização exata do auto-match de nomes (lowercase/acento/plural/gênero) — desde que haja revisão humana.
- Nome/localização e modo de invocação do script seed — mantendo idempotência e persistência dual.
- Termo de query do smoke por marca.

## Deferred Ideas

- Engines de marcas não-suportadas: Wake (Richards, COMP-FUT-01), SFCC (Lacoste/Hugo Boss, COMP-FUT-02), Inditex (Zara, COMP-FUT-03). Spikes SFCC 003-006 são insumo futuro.
- Mapeamento de categorias completo (catálogo inteiro) — futuro, possivelmente atrelado à Phase 29.
- Diagnóstico de saúde de categorias — Phase 29 (DIAG-01/02).
- UI de gestão de marcas — Phase 27 (MGMT-02).
- Frete via checkout VTEX — Phase 30 (FRET-05).
- Todo "reforçar discriminação de modelo" — revisado, não incorporado (relevância de busca por SKU, fora do escopo).
