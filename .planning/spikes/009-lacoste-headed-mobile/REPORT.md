# Spike 009 - Lacoste headed + perfil persistente via rede movel

Gerado em: 2026-06-25T13:26:30.720308+00:00

IP publico de origem (deve ser do celular/4G, nao da Aramis): `187.90.218.121`

## Veredito

**Lacoste:** `PARCIAL_PAGINA_CARREGOU_SEM_PRODUTO`

## Tecnica testada (alavancas gratis)

- Navegador HEADED (janela visivel), nao headless.
- Perfil PERSISTENTE (`launch_persistent_context`) — sessao unica e quente: home primeiro, depois buscas, reaproveitando cookies (`_abck` etc.).
- `playwright_stealth` aplicado, UA/locale `pt-BR`/timezone `America/Sao_Paulo`/headers coerentes.
- Origem: rede de dados moveis (4G/5G), IP fora da rede corporativa.
- Baixa frequencia, sequencial, sem concorrencia.

## Evidencia

| Probe | Status | Bytes | Final URL | Bloqueio | SFCC | Cand. | Prod. | Erro |
|---|---:|---:|---|---|---|---:|---:|---|
| lacoste-home-headed | 200 | 325507 | https://www.lacoste.com/br/ | - | demandware_marker, lacoste_text | 0 | 0 | - |
| lacoste-search-polo-headed | 200 | 325126 | https://www.lacoste.com/br/ | - | demandware_marker, lacoste_text | 3 | 0 | - |
| lacoste-search-camisa-headed | 200 | 325136 | https://www.lacoste.com/br/ | - | demandware_marker, lacoste_text | 3 | 0 | - |


### Produtos consolidados

- Nenhum produto real com titulo + URL Lacoste + preco positivo.


## Decisao do gate

A pagina carregou (sem 403), mas o parser nao extraiu produto. Provavel ajuste de parser/seletor OU render assincrono. Vale uma segunda iteracao do parser, nao desistir ainda.

## Proibicoes respeitadas

- HEADED + perfil persistente foram USADOS (autorizados pelo usuario nesta tentativa gratis).
- NAO foi usado: proxy residencial pago, gateway de scraping pago, CAPTCHA solving, login,
  credenciais privadas, OCAPI/SCAPI nem endpoint interno/mobile privado.
- O spike NAO alterou `backend/` nem `backend/data/brands.json`.
