# Spike Manifest

## Idea
Reduzir falsos positivos na busca por SKU (objetivo: encontrar o MESMO produto Aramis
revendido em marketplaces). Hoje a penalidade de marca em `services/nlp_service.py` é suave
(`score * 0.50`). A hipótese é trocá-la por um **gate rígido de marca** (descartar título sem
a marca da query) — mas isso pode custar **cobertura** (derrubar anúncios legítimos que omitem
a marca no título). Estes spikes medem esse trade-off sobre **dados reais** de buscas passadas
(`data/search_history.json`, 71 jobs cross).

## Requirements
[Decisões que emergiram durante o spiking. Atualizado conforme avança.]

- Objetivo da busca = mesmo produto Aramis (não benchmark de concorrentes). Marca de outra
  fabricante = falso positivo.
- Prioridade: precisão > cobertura ("mostrar menos, mas ter certeza").
- Experimentos devem ser offline/determinísticos sobre histórico real (sem rede/WAF).
- [Spike 001] O gate de marca deve ser um **filtro independente do score visual**. A penalidade
  de texto sozinha é anulada pelo gate de resgate visual (`if img>=85 and text>=40: max(img,text)`)
  — um piquet polo Hering passa a 85 mesmo com texto penalizado a 41.
- [Spike 001] Histórico salvo (`data/search_history.json`) é anterior à penalidade de marca;
  auditorias futuras precisam recalcular scores ao vivo, não confiar nos armazenados.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | brand-gate-impact | standard | Gate rígido de marca sobre 71 result-sets reais: quantos itens saem, classificados em ganho-de-precisão (visual baixo) vs perda-de-cobertura (visual alto) | ✓ VALIDATED | search, relevance, brand |
| 002 | visual-rescue-valve | standard | Válvula de resgate por `image_match_score >= T` sobre itens que o gate derrubaria: recupera legítimos sem readmitir ruído | ✗ INVALIDATED | search, relevance, vision |

| 003 | sfcc-inditex-storefront-mvp | mvp-test | Teste isolado de viabilidade: storefront publico SFCC/Inditex sem API autorizada, sem bypass e sem integrar ao codigo principal | BLOCKED_BY_DIRECT_HTTP_403 | scraping, sfcc, inditex, storefront |
| 004 | sfcc-browser-public-probe | mvp-test | Teste isolado via navegador publico: Hugo Boss e Lacoste carregam home/categoria/produto e expoem dados publicos suficientes para parser SFCC | VALIDATED_FOR_SFCC_PUBLIC_BROWSER | scraping, sfcc, browser, storefront |
| 005 | sfcc-public-parser-prototype | mvp-test | Parser isolado normaliza JSON-LD, OpenGraph e cards visiveis em formato RawProductBronze-like; categorias parciais pedem enriquecimento por PDP | VALIDATED_WITH_DETAIL_PAGE_ENRICHMENT | scraping, sfcc, parser, json-ld |
| 006 | sfcc-live-browser-e2e-prototype | mvp-test | Fluxo vivo via navegador publico: categoria -> ate 3 PDPs por marca -> 6 produtos bronze-ready sem integrar ao codigo principal | VALIDATED_LIVE_E2E_PUBLIC_BROWSER | scraping, sfcc, browser, e2e |

## Prior Art
- `.planning/notes/spike-ean-sku-search.md` — EAN dá 100% precisão mas cobertura ruim (INVALIDADO na prática).
- `.planning/notes/diagnostico-falsos-positivos-busca-sku.md` — diagnóstico das duas causas-raiz.
