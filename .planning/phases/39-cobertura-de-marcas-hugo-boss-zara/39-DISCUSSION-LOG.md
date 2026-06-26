# Phase 39: Cobertura de Marcas — Hugo Boss & Zara - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 39-Cobertura de Marcas — Hugo Boss & Zara
**Areas discussed:** De/para de categorias HB, Descoberta dos paths VTEX, Gate GO/NO-GO da Zara

---

## Seleção de áreas

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| De/para de categorias HB | Onde vive o de/para e quais categorias cobrir | ✓ |
| Descoberta dos paths VTEX | Como obter/validar paths/fq reais | ✓ |
| Monitoramento & falso-positivo | Categorias no scheduler + anti falso "produto novo" | |
| Gate GO/NO-GO da Zara | Critério GO, envelope, query, comportamento | ✓ |

**Notas:** Monitoramento & falso-positivo não selecionada → fica como discrição do planner (criterion #2 ainda obrigatório).

---

## De/para de categorias HB — fonte

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| brand.mappings (dinâmico) | Popular mappings da HB em brands.json; category_mapping.py já faz fallback | ✓ |
| _RAW_CATEGORIES hardcoded | Adicionar HB ao bloco hardcoded junto de aramis/reserva/tommy | |
| Você decide | Planner escolhe pelo padrão das marcas dinâmicas | |

**User's choice:** brand.mappings (dinâmico)
**Notes:** Mantém o hardcoded focado nas marcas da casa; HB é concorrente adicionada.

---

## De/para de categorias HB — escopo de categorias

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Slugs canônicos existentes que a HB tiver | Reusa camisas/polos/camisetas/calcas/bermudas/jaquetas | ✓ |
| Subconjunto core primeiro | Só camisas+polos+camisetas, expandir depois | |
| Tudo que a árvore VTEX expuser | Cobertura máxima, novos slugs (Custom) | |

**User's choice:** Slugs canônicos existentes que a HB tiver
**Notes:** Mantém "banana com banana" cross-marca, sem fragmentar o vocabulário canônico.

---

## Descoberta dos paths VTEX — método

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Auto-descobrir da árvore VTEX + validar | discover_categories/VtexApiClient (VALID_SLUGS-from-RAW) + varredura-amostra | ✓ |
| Mapear manualmente do site | Copiar paths à mão e validar | |
| Auto-descobrir + confirmação humana | Auto-descobrir + preview p/ operador antes de persistir | |

**User's choice:** Auto-descobrir da árvore VTEX + validar
**Notes:** —

---

## Descoberta dos paths VTEX — persistência

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Persistir curado em brands.json | Descoberta única, estático nas varreduras | ✓ |
| Redescobrir em runtime | Resolver árvore VTEX a cada scan | |
| Você decide | Planner escolhe pelo padrão das marcas dinâmicas | |

**User's choice:** Persistir curado em brands.json
**Notes:** Usuário perguntou primeiro "o que é esse de/para?" — explicado (tabela canônico→path/fq por marca) antes de confirmar. Persistir evita chamada extra à árvore VTEX por scan e drift que poderia gerar falso "produto novo".

---

## Gate GO/NO-GO da Zara — critério de GO

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| ≥3 produtos reais + repetição | Espelha gate de ativação v3.0 (D-06) | ✓ |
| ≥1 produto real (mínimo técnico) | Prova rota (D-05), pode não justificar engine | |
| Você decide | Planner define pelo padrão das fases 32/36 | |

**User's choice:** ≥3 produtos reais + repetição
**Notes:** —

---

## Gate GO/NO-GO da Zara — envelope técnico

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Browser público + stealth (igual v3.0) | Playwright + playwright-stealth, storefront público; sem proxy pago/CAPTCHA/login | ✓ |
| Incluir API pública de storefront | Também endpoints públicos não autenticados, se existirem | |
| Você decide | Planner define dentro das fronteiras públicas | |

**User's choice:** Browser público + stealth (igual v3.0)
**Notes:** Spike 008 já obteve 200 + marcador JSON-LD via stealth.

---

## Gate GO/NO-GO da Zara — query padrão

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| polo (fallback camisa) | Mesma query dos gates anteriores | |
| camiseta / calça (mais aderente à Zara) | Categorias mais comuns no catálogo Zara | ✓ |
| Você decide | Planner escolhe query masculina com bom recall | |

**User's choice:** camiseta / calça (mais aderente à Zara)
**Notes:** Maior chance de atingir ≥3 produtos reais.

---

## Gate GO/NO-GO da Zara — escopo em GO

| Opção | Descrição | Selecionada |
|-------|-----------|-------------|
| Construir na própria Phase 39 | Onboard + busca real dentro da fase (criterion #4) | ✓ |
| Spike na 39, engine em fase própria | Promove requisito/fase dedicada para o engine Inditex | |
| Você decide | Planner decide pelo tamanho real do engine | |

**User's choice:** Construir na própria Phase 39
**Notes:** Alinhado ao critério #4 do roadmap; engine é net-new (Inditex).

---

## Claude's Discretion
- Monitoramento HB no scheduler de 10 min e prevenção de falso positivo de "produto novo" (área não selecionada) — reusar mecanismo de scan/comparação existente.
- Nome/estrutura do spike 010, classes, flags, nome do engine Zara (em GO).
- Forma do REPORT.md do spike (veredito GO/NO-GO + evidência reprodutível).
- Local/forma do script de descoberta-e-persistência do de/para da HB.
- Número de tentativas no gate Zara (respeitando baixa frequência).

## Deferred Ideas
- Engine Zara em fase própria (alternativa não escolhida).
- Frete/checkout/estoque por CEP para Zara/Inditex — fora de escopo.
- Proxy residencial/pago/CAPTCHA/browser headed para Zara — requer aprovação explícita.
- Monitoramento HB além das categorias mapeadas (busca por termo, sortimento) — fases 44/45.

### Reviewed Todos (not folded)
- `reforcar-discriminacao-modelo.md` — precisão de discriminação de modelo/NLP; não relacionado a HB/Zara.
- `cap-search-history-list.md` — paginação do histórico de busca; eixo de UX (fases 38/40).
