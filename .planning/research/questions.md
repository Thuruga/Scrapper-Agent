# Research Questions

Perguntas abertas que precisam de investigação mais profunda antes de virar plano.

---

## Sinal de identidade de produto confiável além do EAN (2026-06-13)

**Contexto:** O objetivo da busca é encontrar o MESMO produto Aramis revendido em
marketplaces. O [spike de EAN](../notes/spike-ean-sku-search.md) provou que o EAN dá 100% de
precisão mas **cobertura ruim** (ML retornou 0 itens para o EAN em categoria de moda). O
match textual+visual atual gera falsos positivos (ver
[diagnóstico](../notes/diagnostico-falsos-positivos-busca-sku.md)).

**Pergunta:** Existe algum sinal de identidade de produto mais confiável que texto livre e
menos frágil que EAN para amarrar o produto Aramis ao anúncio do marketplace?

Pistas a investigar:
- Filtro de marca **nativo** nas APIs dos engines (ex: `&brand=Aramis` / atributo de marca
  na query do Mercado Livre/Amazon) — a "Opção 3" pendente do spike de EAN. Reduz ruído na
  origem em vez de filtrar depois?
- IDs de catálogo padronizado do marketplace (ex: catalog_product_id do ML) — quando o anúncio
  está vinculado a um produto de catálogo, há ID estável?
- Atributo de marca declarado pelo seller (estruturado) vs. marca no título livre — qual a
  cobertura real de cada um em moda masculina?
- Referência cruzada por imagem (perceptual hash / CLIP) como chave de identidade quando texto
  e EAN falham.
