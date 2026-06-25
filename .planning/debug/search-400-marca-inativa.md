---
status: resolved
trigger: "POST :8000/search → 400 Bad Request. UI toast: 'Erro na busca: Marcas inválidas: [lacoste]. Marcas suportadas: [aramis, tommy, foxton, ricardoalmeida, bck, reserva, ofcreserva, hering, levis, calvinklein, zapalla, austral, trackfield, richards, hugoboss, mercado_livre, netshoes, amazon]'. (React DevTools msg + gstatic favicon 404 are unrelated noise.)"
created: 2026-06-25
updated: 2026-06-25
slug: search-400-marca-inativa
---

# Debug: /search 400 — "Marcas inválidas: ['lacoste']"

## Symptoms
- **Expected:** A busca não deve oferecer/enviar marcas inativas; `lacoste` está `is_active=false` (Phase 36 anti-bot NO-GO).
- **Actual:** O seletor de marcas da SearchPage lista a Lacoste; ao buscá-la, `POST /search` retorna 400 `Marcas inválidas: ['lacoste']`.
- **Error:** HTTP 400 de `routes_search.py`; toast no frontend.
- **Noise (descartado):** `react-dom-client.development.js` DevTools hint; `t1.gstatic.com/faviconV2 ... buckmanbck.com.br 404` (favicon).
- **Repro:** Tela de busca → selecionar Lacoste (ou reabrir histórico com Lacoste) → buscar.

## Current Focus
- hypothesis: Assimetria de contrato — `GET /brands/` retorna marcas inativas (por design, Phase 25), mas `POST /search` valida só contra `list_brands(active_only=True)`. A SearchPage popula o seletor com a lista completa sem filtrar `is_active`, ao contrário da BannersPage.
- next_action: Filtrar marcas ativas no seletor da SearchPage (chips + "Selecionar Todas"), espelhando o padrão da BannersPage.

## Evidence
- `backend/api/routes_search.py:147-158` (POST), `:241-242` (GET), `:260-268` (export): `all_brands = list_brands(active_only=True) + [mercado_livre, netshoes, amazon]`; brands fora disso → 400.
- `backend/api/routes_brands.py:116-150`: `GET /brands/` chama `list_brands()` SEM `active_only` → inclui inativas (Lacoste). Injeta 3 marketplaces virtuais como `DynamicBrand` (sem is_active explícito).
- `backend/core/models.py:233`: `DynamicBrand.is_active: bool = True` → marketplaces virtuais ficam ativos.
- `frontend/src/api/client.ts:42-44`: `getBrands()` → `/brands/` (lista completa).
- `frontend/src/App.tsx:2270-2274`: `refreshBrands()` guarda a lista completa em `brands` (sem filtro).
- `frontend/src/App.tsx:884` (BannersPage): JÁ filtra `brand.is_active !== false` → padrão correto existente.
- `frontend/src/App.tsx:1280` (SearchPage selector) e `:1138-1140` (`selectAllBrands`): usam `brands.map(...)` SEM filtro de `is_active` → exibem/selecionam Lacoste inativa. **Causa raiz.**

## Eliminated
- hypothesis: `lacoste` hardcoded no frontend — REJEITADA (grep `lacoste` em frontend/src: 0 ocorrências; só em backend `brands.json`/`search_history.json`).
- hypothesis: bug de URL/double-www do SFCC — REJEITADA (erro é validação de marca, não fetch; double-www já resolvido na Phase 31).
- hypothesis: reabrir histórico (search_history.json tem lacoste) re-injeta lacoste em `selectedBrands` → 400 — REJEITADA (App.tsx:1111-1116 só seta `results`/`query`, NÃO `selectedBrands`; reopen apenas exibe resultados antigos, não re-submete).

## Resolution
- root_cause: A SearchPage renderiza o seletor de marcas a partir da lista completa de `GET /brands/` (que inclui inativas por design), mas `POST /search` só aceita marcas ativas. Falta o filtro `is_active !== false` que a BannersPage já aplica.
- fix: Em `frontend/src/App.tsx`, filtrar para marcas ativas no seletor de chips (linha ~1280) e em `selectAllBrands` (linha ~1138). Marketplaces virtuais permanecem (is_active=true).
- verification: `npx tsc -b` no frontend → exit 0 (sem regressão de tipos). Live re-test recomendado (vite faz hot-reload): Lacoste não aparece no seletor; "Selecionar Todas" não inclui Lacoste; busca não retorna mais 400.
- files_changed: frontend/src/App.tsx (selectAllBrands + grid de chips do seletor)
