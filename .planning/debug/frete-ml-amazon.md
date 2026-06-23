---
status: resolved
trigger: "Por que nao esta sendo possivel calcular o frete do mercado livre e da amazon?"
created: 2026-06-11
updated: 2026-06-11
---

# Debug Session: frete-ml-amazon

## Symptoms
- expected: Botão "Calcular Frete" retorna o valor do frete ao clicar
- actual: Retorna "Não foi possível extrair o frete desta página" ou nada visível

## Root Cause (2 problemas distintos)

### 1. Mercado Livre — Login Wall
O ML usa uma URL do tipo `produto.mercadolivre.com.br/MLB-...` que redireciona para
uma página de login/autenticação ("Olá! Para continuar, acesse sua conta") para sessões
sem cookie autenticado. O Playwright headless não tem sessão ativa e o ML bloqueia o 
acesso à PDP completa. Resultado: página tem apenas 35k de HTML com a tela de login,
zero seletores de frete.
No entanto, a API REST pública do ML (`api.mercadolibre.com`) funciona perfeitamente
se requisitada via `curl_cffi` com impersonation. O código forçava uso do Playwright.

### 2. Amazon — CAPTCHA bloqueando headless
A Amazon detecta o Playwright headless e serve uma página de CAPTCHA (5.703 chars de HTML).
O `playwright_stealth` de `calculate_shipping_advanced` nunca foi aplicado pois a linha
`await Stealth().apply_stealth_async(page)` usa a classe `Stealth()` que tem uma API desatualizada; o método correto importado da biblioteca é o módulo-level `stealth_async(page)`.
Isso significa o stealth NUNCA foi ativado para o cálculo de frete da Amazon.

## Evidence
- ML: `"Olá! Para continuar, acesse sua conta"` na página (login wall) via Playwright. API retorna 200 OK via curl_cffi.
- Amazon: CAPTCHA detected = True, HTML com apenas 5703 chars. Stealth falhando silenciosamente por uso incorreto da API.

## Resolution
1. **Amazon (`amazon_engine.py`)**: Corrigida a importação e uso do `playwright_stealth` alterando de `Stealth().apply_stealth_async(page)` para `stealth_async(page)`. Também foram adicionados parâmetros extras de bypass e aumento de wait para evitar CAPTCHAs.
2. **Mercado Livre (`mercado_livre_engine.py`)**: Modificado `calculate_shipping_advanced` para não usar mais Playwright, e sim apontar diretamente para `self.calculate_shipping()`, que usa a API REST oficial do ML simulando o navegador via `curl_cffi`. Isso bypassa a Login Wall instantaneamente com 100% de sucesso.
