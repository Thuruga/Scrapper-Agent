# Spike 010 - Zara: viabilidade de extração pública de produto+preço

Gerado em: 2026-06-29T20:28:18.280612+00:00

## Veredito

**`NO-GO`**

Criterio D-05: GO = >=3 produtos reais (titulo + URL zara.com/br + preco positivo) em AMBAS as rodadas.

## Rodada 1 — query: `camiseta`

### Probes

| Probe | Modo | Status | Bytes | Final URL | Bloqueio | Produtos | Erro |
|---|---|---:|---:|---|---|---:|---|
| zara-search-camiseta-round1 | stealth | 200 | 941840 | https://www.zara.com/br/pt/search?searchTerm=camiseta&section=MAN | - | 0 | - |
| zara-search-calça-round1 | stealth | 200 | 944498 | https://www.zara.com/br/pt/search?searchTerm=cal%C3%A7a&section=MAN | - | 0 | - |


### Produtos extraidos

- Nenhum produto real com titulo nao vazio + URL zara.com/br + preco positivo.


## Rodada 2 — query: `calça`

### Probes

| Probe | Modo | Status | Bytes | Final URL | Bloqueio | Produtos | Erro |
|---|---|---:|---:|---|---|---:|---|
| zara-search-camiseta-round2 | stealth | 200 | 941932 | https://www.zara.com/br/pt/search?searchTerm=camiseta&section=MAN | - | 0 | - |
| zara-search-calça-round2 | stealth | 200 | 944640 | https://www.zara.com/br/pt/search?searchTerm=cal%C3%A7a&section=MAN | - | 0 | - |


### Produtos extraidos

- Nenhum produto real com titulo nao vazio + URL zara.com/br + preco positivo.


## Todos os produtos (consolidado, sem duplicatas)

- Nenhum produto real com titulo nao vazio + URL zara.com/br + preco positivo.


## Tecnicas testadas

- **Browser stealth publico:** Chromium headless + `playwright_stealth.Stealth().apply_stealth_sync(context)`, user-agent desktop Chrome 125, locale `pt-BR`, timezone `America/Sao_Paulo`, viewport 1366x768, headers Accept-Language/Sec-CH-UA coerentes.
- **URL de busca:** `https://www.zara.com/br/pt/search?searchTerm={query}&section=MAN` (section=MAN — filtro masculino D-07/CAT-01).
- **Aguardar carregamento:** `wait_until="domcontentloaded"` + sleep 2.5s + `networkidle` (timeout 8s).
- **Fallback (a) JSON-LD:** Todos os `<script type="application/ld+json">` da pagina de busca inspecionados (ItemList, Product, lista).
- **Fallback (b) Intercepção de rede:** Respostas `application/json` com keywords `search/product/catalog/items` na URL capturadas durante navegação.
- **Fallback (c) Tiles HTML:** BeautifulSoup: links `/br/pt/*.html` em `zara.com/br` + texto aria-label + elemento com classe `price`.
- **Baixa frequencia:** Apenas 2 rodadas, probes sequenciais, sleeps entre tentativas. Sem concorrencia.

## Evidencia de isolamento

- `experiment.py` vive exclusivamente em `.planning/spikes/010-zara-product-price/`.
- Nenhum modulo de `backend/` foi importado (gate D-08/D-10).
- Nenhum arquivo foi gravado dentro de `backend/`.

## Decisao do gate (COMP-07)

Parar execução do Plano 03. Registrar veredito NO-GO com evidência (técnicas testadas + assinatura do bloqueio) e deferir COMP-07 ao backlog. Nenhum código de engine Zara deve ser commitado.

## Proibicoes respeitadas

- Nao foi usado proxy residencial pago, gateway de scraping, CAPTCHA solving, browser headed/manual, perfil persistente real, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado.
- O spike nao alterou `backend/` nem `backend/data/brands.json`.
- Filtro masculino `section=MAN` respeitado em todas as probes (D-07 / CAT-01).
