# Phase 30: Detecção de Engine SFCC & Wake - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 30-Detecção de Engine SFCC & Wake
**Areas discussed:** Detecção SFCC (HTTP 403), Ordem das probes & falsos positivos, Ativa sem engine (janela 30→31/32)

---

## Seleção de áreas (gray areas)

| Área | Discutida |
|------|-----------|
| Detecção SFCC (HTTP 403) | ✓ |
| Ordem das probes & falsos positivos | ✓ |
| Ativa sem engine (janela 30→31/32) | ✓ |
| Detecção Wake (marker CDN) | — (não selecionada; default registrado: marker-only → `wake`) |

---

## Detecção SFCC (HTTP 403)

### Q1 — Mecanismo de obtenção do sinal SFCC (HTTP=403)

| Option | Description | Selected |
|--------|-------------|----------|
| Browser render (Playwright) | Renderiza a home e procura marcadores demandware; único caminho validado pelos spikes; consistente com Phase 31; custo: sobe browser no cadastro. | ✓ |
| Inspecionar o próprio 403 | Olha status/headers/corpo do 403; barato; alto risco SC-4 (Zara/Inditex também 403). | |
| Allowlist de domínios SFCC | Mapa configurável de domínios conhecidos; pragmático para 2 marcas; não genérico; manutenção manual. | |

**User's choice:** Browser render (Playwright)
**Notes:** Alinhado ao engine browser-rendered da Phase 31; home renderizada já expõe os sinais (spike 004).

### Q2 — Marcador que crava o veredito `sfcc`

| Option | Description | Selected |
|--------|-------------|----------|
| Host de assets demandware | `demandware.static` / `demandware.edgesuite.net`; espelha vtexassets.com/cdn.shopify.com; respeita T-25-01; mais robusto. | ✓ |
| Path /on/demandware.store/ | Assinatura de URL de storefront SFCC; exclusivo mas depende de links na home; mais frágil. | |
| Substring `demandware` (ampla) | Qualquer ocorrência; maior recall, leve perda de precisão. | |
| Você decide | Deixar o marcador exato pro planner, desde que exclusivo e cumpra SC-4. | |

**User's choice:** Host de assets demandware
**Notes:** Reaproveitar `BrowserManager` existente; render falha/timeout → unknown (sem crash) registrado como diretriz.

---

## Ordem das probes & falsos positivos

### Q1 — Quando o probe SFCC (browser) dispara

| Option | Description | Selected |
|--------|-------------|----------|
| Sempre como última probe | Após Shopify→VTEX→HTML falharem, sobe o browser como passo final; determinístico; custo só em cadastros de site realmente-unknown. | ✓ |
| Só quando a home der 403 | Browser apenas se home retornou 403/401/challenge; mais eficiente; risco mínimo de perder SFCC sem 403. | |
| Você decide | Diretriz last-resort + render-fail→unknown; gatilho fino pro planner. | |

**User's choice:** Sempre como última probe
**Notes:** SC-4 sustentado pela combinação marcador exclusivo + last-resort. Wake permanece no probe HTML, virando o retorno `fbitsstatic.net` → `wake`.

---

## Ativa sem engine (janela 30→31/32)

### Q1 — Tratamento da marca sfcc/wake ativa sem engine

| Option | Description | Selected |
|--------|-------------|----------|
| Guard explícito na factory | Branch sfcc/wake na EngineFactory que falha de forma clara em vez de cair no VTEXEngine silencioso; corrige fallback-pra-VTEX latente; pouco escopo extra. | ✓ |
| Aceitar a janela transitória | Phase 30 só rotula; fallback VTEXEngine retorna 0/erro capturado; 31/32 fecham a janela; escopo mínimo. | |
| Você decide | Registrar trade-off e deixar a chamada pro planner. | |

**User's choice:** Guard explícito na factory
**Notes:** Guard cobre sfcc E wake; não pode quebrar vtex/shopify/marketplaces virtuais. Forma exata (exceção vs. sentinela) é detalhe do planner.

---

## Claude's Discretion

- Gatilho fino do probe SFCC ("sempre" decidido; planner pode otimizar para "só em 403" se o custo incomodar, preservando SC-1/SC-4).
- Forma exata do guard da factory (exceção custom vs. engine sentinela diagnosticável).
- Nomes de constantes/markers e estrutura dos novos testes (seguir convenções do repo).

## Deferred Ideas

- Confirmação GraphQL + `TCS-Access-Token` da Wake → spike gating Phase 32.
- Engines de extração SFCC (Phase 31) e Wake (Phase 32).
- Zara/Inditex IOP (COMP-FUT-03, deferido).
- Otimização "só em 403" do probe SFCC (refino futuro, não comprometido).
- Todo "Reforçar discriminação de modelo" — revisado, NÃO incorporado (off-topic: busca por SKU, não detecção de engine; arquivo inexistente).
