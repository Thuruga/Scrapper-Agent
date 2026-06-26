# Spike 008 - Lacoste anti-bot + Zara recheck

Gerado em: 2026-06-25T02:17:10.729642+00:00

## Veredito

**Lacoste:** `NO-GO`

**Zara:** `PROMOVER_REQUISITO_FUTURO`

## Lacoste

Query usada para decisao: `polo`

### Rodada 1

- Nenhum produto real com titulo + URL Lacoste + preco positivo.


### Rodada 2

- Nenhum produto real com titulo + URL Lacoste + preco positivo.


## Zara

Resultado: `PROMOVER_REQUISITO_FUTURO`

| Probe | Modo | Status | Bytes | Final URL | Bloqueio | SFCC | Erro |
|---|---|---:|---:|---|---|---|---|
| zara-home-stealth | stealth | 200 | 1734637 | https://www.zara.com/br/ | - | jsonld_product_marker | - |
| zara-search-stealth | stealth | 200 | 960113 | https://www.zara.com/br/pt/search?searchTerm=polo&section=WOMAN | - | - | - |


Zara foi apenas reavaliada. Nenhum engine Zara foi criado e nenhum endpoint interno/mobile privado foi usado.

## Tecnicas testadas

- Baseline Playwright publico: Chromium headless, contexto desktop pt-BR e fingerprint masking basico equivalente ao BrowserManager.
- Stealth publico permitido: `playwright_stealth.Stealth().apply_stealth_sync(context)`, user-agent desktop, locale `pt-BR`, timezone `America/Sao_Paulo`, viewport 1366x768, headers Sec-CH-UA/Accept-Language coerentes.
- Baixa frequencia: probes sequenciais com sleeps curtos; sem concorrencia.

## Evidencia

### Probes Lacoste

| Probe | Modo | Status | Bytes | Final URL | Bloqueio | SFCC | Erro |
|---|---|---:|---:|---|---|---|---|
| lacoste-home-baseline | baseline | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |
| lacoste-search-polo-baseline | baseline | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |
| lacoste-search-camisa-baseline | baseline | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |
| lacoste-home-stealth | stealth | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |
| lacoste-search-polo-stealth | stealth | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |
| lacoste-search-camisa-stealth | stealth | 403 | 296 | https://www.lacoste.com/br/ | http_status_403, access_denied_text, akamai_reference, html_below_1000_bytes | lacoste_text | - |


### Produtos Lacoste consolidados

- Nenhum produto real com titulo + URL Lacoste + preco positivo.


## Decisao do gate

Parar a phase, manter lacoste.is_active=false e nao executar 36-02/36-03.

## Proibicoes respeitadas

- Nao foi usado proxy residencial, gateway pago de scraping, CAPTCHA solving, browser headed/manual, perfil persistente real, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado.
- O spike nao alterou `backend/` nem `backend/data/brands.json`.
