# Spike 007 — Wake GraphQL Token Confirmation

## Veredito
**GO**

>= 1 produto com titulo + URL + preco retornado via GraphQL com header `TCS-Access-Token` (D-02 atendido). Alvo: **Richards**.

## Evidencia

- **Endpoint:** `https://storefront-api.fbits.net/graphql`
- **Header:** `TCS-Access-Token: tcs_richa_35...` (extraido de: `https://www.richards.com.br`)
- **Estrategia de extracao:** regex storefrontAccessToken (primaria)
- **HTTP status (home page):** 200
- **HTTP status (GraphQL):** 200
- **Query:** `search(query: "camisa", first: 5)` via variaveis GraphQL
- **Produtos retornados:** 5

### Produtos extraidos (amostra)

**Produto 1:**
- productName: `Camisa Linho Hortencia`
- aliasComplete (raw): `produto/camisa-linho-hortencia-196863`
- URL construida: `https://www.richards.com.br/produto/camisa-linho-hortencia-196863`
- prices.price (raw): `479`
- images.url: `https://richards.fbitsstatic.net/img/p/camisa-linho-hortencia-196863/548230.jpg?w=420&h=420&v=202511181600`
- available: `True`

**Produto 2:**
- productName: `Camisa Linho Gelo`
- aliasComplete (raw): `produto/camisa-linho-gelo-196853`
- URL construida: `https://www.richards.com.br/produto/camisa-linho-gelo-196853`
- prices.price (raw): `479`
- images.url: `https://richards.fbitsstatic.net/img/p/camisa-linho-gelo-196853/548222.jpg?w=420&h=420&v=202511181505`
- available: `True`

**Produto 3:**
- productName: `Camisa Linho Melancia`
- aliasComplete (raw): `produto/camisa-linho-melancia-196867`
- URL construida: `https://www.richards.com.br/produto/camisa-linho-melancia-196867`
- prices.price (raw): `479`
- images.url: `https://richards.fbitsstatic.net/img/p/camisa-linho-melancia-196867/548073.jpg?w=420&h=420&v=202511181411`
- available: `True`

## Campos confirmados

| Campo | Disponivel | Valor exemplo |
|-------|-----------|---------------|
| productName | sim | `Camisa Linho Hortencia` |
| aliasComplete | sim | `produto/camisa-linho-hortencia-196863` |
| prices.price | sim | `479` |
| images.url | sim | `https://richards.fbitsstatic.net/img/p/camisa-linho-hortenci` |
| available | sim | `True` |

## Formato do preco

- Valor bruto retornado pela API: `479`
- Unidade: **CONFIRMADO — float em reais (valor abaixo de 10000, compativel com preco de produto de moda)**
- Resolucao A4: CONFIRMADO (float em reais)

## Token auto-extraido

- **Estrategia:** regex storefrontAccessToken (primaria)
- **Token encontrado em:** `https://www.richards.com.br`
- **Prefixo observado:** `tcs_richa_35...` (mascara — token completo omitido, T-32-03)
- **Resolucao A1:** CONFIRMADO — token extraido aceito pelo endpoint GraphQL
- **Resolucao A5:** CONFIRMADO — Richards usa padrao SDK Wake (storefrontAccessToken no HTML)

## Alvo testado

- [x] Richards (www.richards.com.br) — GO — sucesso

## Resolucao das suposicoes A1-A6

| # | Suposicao | Resultado |
|---|-----------|-----------|
| A1 | storefrontAccessToken == TCS-Access-Token aceito pelo GraphQL | CONFIRMADO |
| A2 | aliasComplete disponivel em search.products.edges.node | CONFIRMADO |
| A3 | images.url disponivel em search.products.edges.node | CONFIRMADO |
| A4 | prices.price em reais como float | CONFIRMADO (float < 10000, interpretado como reais) |
| A5 | Richards expoe storefrontAccessToken no HTML (padrao SDK Wake) | CONFIRMADO (Richards: regex storefrontAccessToken (primaria)) |
| A6 | Busca nao exige reCAPTCHA/sessao alem do TCS-Access-Token | CONFIRMADO — busca retornou produtos sem reCAPTCHA ou sessao adicional |
