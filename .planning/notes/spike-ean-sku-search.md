---
title: Spike - Busca de SKU por EAN
date: 2026-06-10
context: Melhoria na busca por SKU para resolver falsos positivos (cobertura vs precisão)
---

# Spike: Busca de SKU por EAN nos Marketplaces

## O Problema
Ao buscar por um SKU da Aramis (ex: `PO.10.0278010`), o sistema identifica o nome do produto na API da Aramis (ex: "Polo Manga Curta Básica Piquet Marinho"), porém os marketplaces (Mercado Livre, Amazon) frequentemente ignoram a palavra "Aramis" anexada e retornam produtos genéricos concorrentes, como da Hering.

## Hipótese (Spike 1)
Usar a API da Aramis para extrair o **EAN** (Código de Barras Universal) atrelado ao SKU, e em seguida buscar nos marketplaces utilizando o EAN em vez de string de texto. O EAN garantiria 100% de precisão (match exato).

## Resultados da Investigação

1. **Aramis (VTEX) retorna EAN?**
   - **SIM**. Realizamos chamadas à API nativa da Aramis (`/api/catalog_system/pub/products/search?ft=PO.10.0278010`).
   - A API retorna com sucesso um EAN distinto para cada variação de tamanho (P, M, G, GG). Exemplo de EAN retornado: `7909790935826`.

2. **Marketplaces indexam esse EAN na Busca?**
   - **NÃO DE FORMA CONFIÁVEL**.
   - Executamos consultas de teste nas APIs de busca do **Mercado Livre** utilizando o EAN extraído `7909790935826`.
   - **Resultado:** A API do ML retornou **0 itens encontrados**.
   - **Motivo:** Na categoria de Moda (Vestuário), sellers terceiros frequentemente falham em preencher o atributo Universal/EAN de forma correta nos marketplaces, ou a plataforma não o indexa com peso suficiente para busca de texto livre, a menos que o catálogo padrão seja usado rigorosamente.

## Conclusão
A abordagem via EAN, apesar de garantir 100% de precisão, **sofre com baixa cobertura nos marketplaces**. Muitos produtos oficiais que estão lá não seriam encontrados.

## Próximos Passos
A opção 1 falhou no teste prático de cobertura externa. Portanto, para resolver a dor dos "falsos positivos", devemos recorrer às opções 2 e 3 discutidas anteriormente:

- **Option 2:** Filtro Rígido Pós-Busca (Remover do frontend resultados cujo título não possua a marca).
- **Option 3:** Filtro Nativo de URL (Injetar a flag `&brand=Aramis` nas APIs dos motores).
