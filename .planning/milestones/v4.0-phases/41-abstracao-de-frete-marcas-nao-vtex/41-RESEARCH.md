# Phase 41: Abstracao de Frete & Marcas Nao-VTEX - Research

**Pesquisado em:** 2026-06-29
**Dominio:** Frete por provider para Wake e Shopify, preservando VTEX
**Confianca geral:** MEDIUM (Shopify docs oficiais claras; Wake tem endpoint oficial, mas precisa prova por loja/Richards)

---

<user_constraints>
## Restricoes do Usuario (de CONTEXT.md)

### Decisoes Travadas

- **D-01:** Criar `backend/services/shipping/` com `BaseShipping`, `WakeShipping`, `ShopifyShipping` e resolver central por engine.
- **D-02:** VTEX permanece no `VtexApiClient` e em `services/vtex_shipping.py`; nao mover VTEX para a nova abstracao.
- **D-03:** Providers nao-VTEX retornam contrato conceitual `{"state": str, "shipping_options": List[ShippingInfo]}`.
- **D-04:** `0.0` e frete gratis; `None` e nao calculado. Nunca mascarar falha como gratis.
- **D-05/D-06:** Buckman/BCK e Shopify. A mencao "Buckman (VTEX)" no roadmap e erro de contexto.
- **D-08/D-09:** Richards e alvo Wake; reusar token/identidade Wake ja existente.
- **D-10/D-11:** SFCC/Lacoste fica unsupported nesta fase.
- **D-12/D-15:** Comecar com spike-gate curto, baixa frequencia, sem credenciais privadas e sem bypass anti-bot.
- **D-16/D-17:** Suportar frete inline e sob demanda pelo mesmo resolver/provider sem quebrar `/search/calculate-shipping-vtex`.
- **D-18:** Providers aceitam URL do produto como entrada primaria e descobrem internamente variant/SKU/etc.
- **D-19/D-21:** Reusar UX, `DEFAULT_CEP`, validacao de CEP e copy da Phase 33.

### Discricao do Planner

- Nome exato de classes/dataclasses internas.
- Se providers compartilham helpers de parse.
- Se on-demand sera endpoint novo ou generalizacao. Este plano escolhe endpoint novo: `/search/calculate-shipping-brand`, para nao tocar no contrato VTEX.
- Exata forma do spike 011. Este plano escolhe um `experiment.py` unico com probes Shopify e Wake independentes.

### Fora do Escopo

- Marketplaces e matriz multi-regional: Phase 42.
- SFCC/Lacoste shipping real.
- Proxy pago, CAPTCHA, login, credenciais privadas.
- Refatorar VTEX para `BaseShipping`.
- Destaque de preco total/landed price como fluxo principal.
</user_constraints>

<phase_requirements>
## Requisitos da Phase

| ID | Descricao | Suporte da Pesquisa |
|----|-----------|---------------------|
| FRET-07-a | Existe `BaseShipping` com providers Wake/Shopify e resolver por engine. | Baixo risco de arquitetura; padrao local de factory/engines ja existe. |
| FRET-07-b | Busca Richards/Wake retorna custo e prazo quando provider der GO. | Depende de spike Wake: endpoint oficial de cotacao existe, mas loja/token/produto real precisam casar. |
| FRET-07-c | Buckman/BCK tem frete calculado e exibido. | Buckman e Shopify; docs oficiais do Ajax Cart cobrem variant add + shipping rates, mas loja pode bloquear. |
| FRET-07-d | VTEX atual permanece funcionando. | Exige regressao hermetica dos testes Phase 33 e proibicao de rotear VTEX pela nova abstracao. |
</phase_requirements>

---

## Sumario

Esta fase deve separar duas coisas que parecem iguais, mas tem riscos diferentes:

1. **Abstracao interna:** criar um contrato comum de shipping nao-VTEX, resolver por engine, provider unsupported e testes hermeticos. Isso e controlado e deve ser implementado mesmo se algum provider real der NO-GO.
2. **Cotacao real por loja:** provar que Buckman/Shopify e Richards/Wake conseguem cotar frete publicamente com produto real e CEP. Isso depende de sessao/carrinho, disponibilidade e possiveis regras por loja; por isso entra antes como spike 011.

**Shopify:** a documentacao oficial do Ajax Cart indica o caminho publico: adicionar variante ao carrinho via `POST /{locale}/cart/add.js`; gerar frete com `POST /{locale}/cart/prepare_shipping_rates.json`; ler resultado com `GET /{locale}/cart/async_shipping_rates.json`. Tambem existe `GET /{locale}/cart/shipping_rates.json`, mas a propria doc recomenda o par prepare/async e observa throttling no endpoint direto. O provider deve descobrir `variant_id` via produto `.json`, usar uma sessao isolada, limpar o carrinho ao fim e normalizar `shipping_rates` para `ShippingInfo`.

**Wake:** a documentacao oficial Wake/Fbits expoe `POST https://api.fbits.net/fretes/cotacoes`, com query params `cep`, `tipoIdentificador` (`Sku` ou `ProdutoVarianteId`) e body com `valorTotal` e `produtos`. O spike deve provar se Richards permite esse caminho com as credenciais/token publicos ja usados no `WakeEngine`, e qual identificador real o produto exposto no catalogo fornece. Se a API exigir credencial privada ou escopo nao disponivel, Wake recebe NO-GO/unsupported com evidencia.

**VTEX:** deve ficar intocado. A nova camada nasce ao lado, nao em volta. O risco principal de regressao e algum caller decidir mandar VTEX pelo resolver generico; os planos bloqueiam isso com teste de resolver e testes Phase 33.

---

## Mapa de Responsabilidade Arquitetural

| Capacidade | Tier Primario | Tier Secundario | Racional |
|------------|---------------|-----------------|----------|
| Descoberta de provider por engine | Backend `services/shipping/resolver.py` | `brand_service`/modelos | Centraliza decisao Wake/Shopify/unsupported. |
| Cotacao Shopify/Buckman | Backend `ShopifyShipping` | Spike 011 | Usa Ajax Cart publico com sessao isolada e variant id descoberto por URL. |
| Cotacao Wake/Richards | Backend `WakeShipping` | `WakeEngine` token/dominio | Usa cotacao Wake/Fbits se spike provar identificador + acesso. |
| Populacao inline | `ShopifyEngine` / `WakeEngine` | `EngineFactory.search_all_brands` | `zipcode/include_shipping` ja propagam; engines nao-VTEX chamam provider. |
| Frete sob demanda | `backend/api/routes_search.py` | Frontend client/modal | Endpoint novo por marca evita mexer no endpoint VTEX. |
| Renderizacao | `frontend/src/App.tsx` | store/client | Reusa renderer `shipping_options` Phase 33. |
| VTEX | `VtexApiClient` | `services/vtex_shipping.py` | Permanece dono exclusivo do frete VTEX. |

---

## Stack Padrao

Nenhum pacote novo e necessario.

| Componente | Em uso | Papel |
|------------|--------|-------|
| `aiohttp`/sessao async existente | backend | HTTP baixo nivel dos providers, seguindo padroes atuais. |
| `pydantic` | backend | `ShippingInfo`, `SearchProductResult` e response models. |
| `pytest` | backend | Testes hermeticos com fake session/provider. |
| React/Vite | frontend | Reuso de modal/estado de frete. |

### Auditoria de Pacotes

Nao instalar dependencias novas nesta fase. Spikes devem reutilizar bibliotecas existentes no projeto. Se Playwright for usado no spike, deve ser apenas para sessao/cookie publica e registrado como fallback; o caminho preferencial e HTTP API.

---

## Integracao com Codigo Existente

### Modelos e contrato

- `backend/core/models.py` ja tem `ShippingInfo`, `shipping_options`, `shipping`, `shipping_price`, `is_free_shipping` e `landed_price`.
- Providers devem retornar `ShippingInfo` ja normalizado. O caller aplica a opcao primaria nos campos legados.
- Estados minimos: `available`, `unavailable_for_cep`, `temporary_failure`, `unsupported`.

### Engines

- `EngineFactory.search_all_brands(... zipcode, include_shipping)` ja passa os argumentos.
- `WakeEngine.calculate_shipping` e `ShopifyEngine.calculate_shipping` hoje sao no-op/None. A fase substitui apenas estes engines.
- `VtexApiClient.calculate_for_brand` e `_fetch_shipping` continuam como estao.

### API

- `/search/calculate-shipping-vtex` continua inalterado.
- Novo endpoint sugerido: `/search/calculate-shipping-brand`, com `brand_key`, `product_url`, `zipcode` e campos opcionais aditivos quando o spike provar necessidade.
- O backend deve validar que `product_url` pertence ao dominio persistido da marca antes de qualquer request externo.

### Frontend

- O frontend ja sabe exibir `shipping_options` e estados especiais.
- Mudanca principal: habilitar calculo sob demanda para Wake/Shopify suportados, sem mostrar botao real para SFCC/unsupported.

---

## Arquitetura de Validacao

### Hermetico

- Resolver retorna provider correto para `engine="wake"`, `engine="shopify"` e `UnsupportedShipping` para `sfcc`/desconhecido.
- Providers parseiam payloads fake e retornam `shipping_options` ordenado.
- Falhas de provider viram `temporary_failure`, nao exception que derruba a busca.
- `None` nao vira gratis; `0.0` vira gratis somente quando a origem explicita preco zero.
- Endpoint novo valida CEP e ancora host no dominio da marca.
- Testes Phase 33 continuam verdes para VTEX.

### Ao Vivo / Manual

- Spike 011 registra GO/NO-GO por provider com data, dominio, produto, caminho testado, response signature e cuidado de baixa frequencia.
- Manual smoke pos-implementacao: Buckman e Richards com CEP padrao populam ou retornam estado explicito.

---

## Fontes Externas Oficiais

- Shopify Ajax Cart API: `https://shopify.dev/docs/api/ajax/reference/cart`
  - Relevante: `cart/add.js` aceita variant id e quantidade; `prepare_shipping_rates.json` + `async_shipping_rates.json` geram/retornam fretes; `shipping_rates.json` existe mas e sujeito a throttling.
- Wake/Fbits cotacao de frete: `https://wakecommerce.readme.io/reference/realiza-uma-cotacao-de-frete`
  - Relevante: endpoint `POST https://api.fbits.net/fretes/cotacoes`, query params `cep`, `tipoIdentificador`, `retiradaLoja`, body `valorTotal` + `produtos`.

---

## Riscos e Perguntas Fechadas pelo Plano

| Risco | Tratamento |
|-------|------------|
| Buckman esta no roadmap como VTEX | Contexto corrige para Shopify; testes/planos usam `bck` como Shopify. |
| Shopify shipping depende de sessao/carrinho | Spike cria sessao isolada, limpa carrinho e documenta cookies/locale usados. |
| Wake exige API key privada | Spike declara NO-GO para Wake real e implementa unsupported/temporary failure sem fake data. |
| Produto nao tem variant/SKU publico | Provider descobre via product URL; se nao descobrir, retorna `unsupported`/`temporary_failure` conforme causa. |
| SSRF via product_url sob demanda | Validar host contra dominio da marca e nao aceitar URL arbitraria. |
| Regressao VTEX | Resolver nao roteia VTEX; testes Phase 33 obrigatorios. |
