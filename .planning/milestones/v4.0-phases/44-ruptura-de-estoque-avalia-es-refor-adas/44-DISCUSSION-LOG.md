# Phase 44: Ruptura de Estoque & Avaliações Reforçadas - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 44-Ruptura de Estoque & Avaliações Reforçadas
**Areas discussed:** Métrica de ruptura por marca, Operação do cart-probe, Comentários de avaliações

---

## Métrica de ruptura por marca

### Denominador do percentual

| Option | Description | Selected |
|--------|-------------|----------|
| Só produtos com estoque verificado | `rupture_pct = esgotados / (em_estoque + esgotados)`, com `não verificado` separado. | ✓ |
| Todos os produtos varridos | `rupture_pct = esgotados / total`, com risco de diluir lacunas de engine. | |
| Você decide | Delegar a fórmula ao planner. | |

**User's choice:** Só produtos com estoque verificado.
**Notes:** Mantém `stock_availability=None` fora do denominador.

### Fonte da verdade

| Option | Description | Selected |
|--------|-------------|----------|
| Resumo persistido por varredura | Salvar `total`, `in_stock`, `out_of_stock`, `unknown_stock` e `rupture_pct`. | ✓ |
| Só resposta/log da varredura | Mais leve, mas sem histórico. | |
| UI completa já nesta fase | Mais operacional, porém aumenta escopo frontend. | |

**User's choice:** Resumo persistido por varredura.
**Notes:** Deve servir para varredura manual e scheduler.

### Engines sem verificação

| Option | Description | Selected |
|--------|-------------|----------|
| Entram com `unknown_stock` | Marca aparece, mas não afeta ruptura; `rupture_pct` pode ser `null`. | ✓ |
| Falha da marca no relatório | Tratar ausência de estoque como erro/unsupported. | |
| Excluir do resumo | Mais limpo, mas esconde lacuna de cobertura. | |

**User's choice:** Entram com `unknown_stock`.
**Notes:** Lacuna de estoque não é falha de catálogo/preço.

### Variações e tamanhos

| Option | Description | Selected |
|--------|-------------|----------|
| Disponível se qualquer variação tiver estoque | Padrão próximo ao VTEX atual (`AvailableQuantity > 0`). | ✓ |
| Esgotado se variação principal sem estoque | Mais rígido e possivelmente falso. | |
| Separar produto e tamanho | Métrica mais rica, mas maior escopo. | |

**User's choice:** Disponível se qualquer variação tiver estoque.
**Notes:** Produto só é esgotado se nenhuma variação disponível for encontrada.

---

## Operação do cart-probe

### Gatilho operacional

| Option | Description | Selected |
|--------|-------------|----------|
| Sob demanda em produto específico | Menor risco; parte de uma varredura controlada. | ✓ |
| Lote pequeno selecionado | Útil, mas exige fila/controle maior. | |
| Automático na varredura controlada | Completo, mas caro e arriscado. | |

**User's choice:** Sob demanda em produto específico.
**Notes:** Não rodar cart-probe em massa por padrão.

### Persistência do resultado

| Option | Description | Selected |
|--------|-------------|----------|
| No registro da varredura/produto | Campos de estimate/state/timestamp no produto do scan. | ✓ |
| Só resposta imediata da ação | Simples, sem rastreabilidade. | |
| Tabela própria de probes | Melhor auditoria longa, maior escopo. | |

**User's choice:** No registro da varredura/produto.
**Notes:** Mantém histórico auditável sem mudar busca ao vivo.

### Limite operacional

| Option | Description | Selected |
|--------|-------------|----------|
| Conservador por padrão | 1 produto por ação, throttle, timeout curto, cleanup, N pequeno configurável. | ✓ |
| Fila por marca com limite maior | Mais produtivo, mais controle. | |
| Sem limite além do throttle | Risco alto para checkout/anti-bot. | |

**User's choice:** Conservador por padrão.
**Notes:** Planner escolhe N pequeno.

### Estados de falha/ausência

| Option | Description | Selected |
|--------|-------------|----------|
| Estados explícitos | `estimated`, `unavailable`, `unsupported`, `blocked`, `temporary_failure`. | ✓ |
| Só `null` + mensagem | Simples, mas ruim para métricas/debug. | |
| Falhar a ação inteira | Atrito alto quando só um produto falha. | |

**User's choice:** Estados explícitos.
**Notes:** Nunca inventar quantidade.

---

## Comentários de avaliações

### Momento da busca de comentários

| Option | Description | Selected |
|--------|-------------|----------|
| Sob demanda por produto | Busca/varredura trazem resumo; comentários vêm quando o operador pede. | ✓ |
| Inline na busca por produto | Completo, mas lento/frágil. | |
| Inline só na varredura controlada | Bom para auditoria, mistura peso com scan. | |

**User's choice:** Sob demanda por produto.
**Notes:** `rating` e `review_count` permanecem resumo leve.

### Conteúdo mínimo

| Option | Description | Selected |
|--------|-------------|----------|
| Estruturado e compacto | `review_id`, `rating`, `title`, `text`, `author`, `created_at`, provider/ref. | ✓ |
| Texto bruto + nota | Simples, pouco dedup/análise. | |
| Payload bruto completo | Pesado e com maior risco de dados pessoais. | |

**User's choice:** Estruturado e compacto.
**Notes:** Evitar persistência de payload bruto por padrão.

### Paginação

| Option | Description | Selected |
|--------|-------------|----------|
| Configurável com default pequeno | 1 ou 2 páginas por produto; dedup por `review_id`. | ✓ |
| Sempre uma página | Seguro, menos flexível. | |
| Até acabar | Completo, risco alto. | |

**User's choice:** Configurável com default pequeno.
**Notes:** Atende o roadmap sem abuso de provider.

### Marcas sem provider

| Option | Description | Selected |
|--------|-------------|----------|
| Provider audit + `unsupported` explícito | Configurar conhecidos; sem caminho vira estado. | ✓ |
| Heurística genérica HTML/PDP | Pode descobrir, mas instável/caro. | |
| Ignorar silenciosamente | Esconde cobertura real. | |

**User's choice:** Provider audit + `unsupported` explícito.
**Notes:** Marcas sem provider não quebram busca.

---

## Claude's Discretion

- Nome exato de campos, endpoints e modelos.
- Local final da persistência, condicionado ao estado real da Phase 37/SQLite.
- Defaults exatos de `max_review_pages`, timeout e throttle, desde que conservadores.

## Deferred Ideas

- UI completa de analytics de ruptura.
- Cart-probe automático ou em lote grande.
- Ruptura por SKU/tamanho como métrica principal.
- Payload bruto completo de reviews.
- Heurística genérica agressiva para reviews sem provider.
