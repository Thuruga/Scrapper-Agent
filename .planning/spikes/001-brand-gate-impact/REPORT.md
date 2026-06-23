# Spike 001 — Impacto do Gate Rígido de Marca (dados reais)

- Jobs cross analisados: **71**
- Itens exibidos (total): **1454**
- Limiares: PERDA_COBERTURA img>=`85` | GANHO_PRECISAO img<`60`

## Resultado do gate rígido (entre itens com gate aplicável)

| Métrica | Itens | % do aplicável |
|---|---|---|
| Gate aplicável (query tem marca) | 1454 | 100% do total |
| Marca presente (mantidos) | 1376 | 95% |
| Marca ausente (DESCARTADOS) | 78 | 5% |
| → Ganho de precisão (img<60) | 4 | 0% |
| → Perda de cobertura (img>=85) | 1 | 0% |
| → Ambíguo | 73 | 5% |
| Descartados que nomeiam concorrente | 11 | 14% dos descartados |

## Por marketplace

| Marketplace | Exibidos | Descartados | → Precisão | → Cobertura |
|---|---|---|---|---|
| Netshoes | 665 | 0 | 0 | 0 |
| Mercado Livre | 407 | 57 | 4 | 0 |
| Amazon | 382 | 21 | 0 | 1 |

## Amostra — GANHO DE PRECISÃO (descartados, visual baixo)

| txt | img | fin | marca? | concorrente? | título |
|---|---|---|---|---|---|
| 62 | 58 | 61 | NÃO | - | Kit 3 Camisas Infantis Polo Piquet Algodão Manga Curta |
| 62 | 58 | 61 | NÃO | - | Kit 3 Camisas Infantis Polo Piquet Algodão Manga Curta |
| 62 | 58 | 61 | NÃO | - | Kit 3 Camisas Infantis Polo Piquet Algodão Manga Curta |
| 62 | 58 | 61 | NÃO | - | Kit 3 Camisas Infantis Polo Piquet Algodão Manga Curta |

## Amostra — PERDA DE COBERTURA (descartados, visual alto)

| txt | img | fin | marca? | concorrente? | título |
|---|---|---|---|---|---|
| 68 | 88 | 76 | NÃO | - | Tênis masculino Sanders Soft Back Slip On, Camurça verde Syc |

## Amostra — AMBÍGUOS (descartados, visual médio)

| txt | img | fin | marca? | concorrente? | título |
|---|---|---|---|---|---|
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 88 | 85 | 86 | NÃO | sim | Camisa Polo Básica Masculina Manga Curta Em Piquet Hering |
| 46 | 84 | 61 | NÃO | - | Camiseta Polo Manga Curta Com Ziper Masculina Malha Canelada |
| 46 | 84 | 61 | NÃO | - | Camiseta Polo Manga Curta Com Ziper Masculina Malha Canelada |
| 46 | 84 | 61 | NÃO | - | Camiseta Polo Manga Curta Com Ziper Masculina Malha Canelada |
| 46 | 84 | 61 | NÃO | - | Camiseta Polo Manga Curta Com Ziper Masculina Malha Canelada |
| 46 | 83 | 61 | NÃO | - | Camisa polo masculina manga curta casual moda slim fit, Azul |
| 46 | 83 | 61 | NÃO | - | Camisa polo masculina manga curta casual moda slim fit, Azul |
