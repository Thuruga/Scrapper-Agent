# Phase 37: Paridade de Atributos & Fundação SQLite - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** 37-Paridade de Atributos & Fundação SQLite
**Areas discussed:** Vocabulário canônico v1, Escopo do SQLite / fronteira da phase

---

## Vocabulário canônico v1

| Option | Description | Selected |
|--------|-------------|----------|
| Nucleo enxuto | `color`, `fit`, `material`, `composition`, `gender`, `size` | |
| Nucleo expandido | Campos do núcleo + `pattern`, `sleeve_length`, `collar`, `occasion` | |
| Nucleo minimo | `color`, `material`, `size` | |
| Lista livre do usuário | Travar os campos obrigatórios a partir da necessidade real de exportação | ✓ |

**User's choice:** Lista livre em vez dos pacotes sugeridos.
**Notes:** O usuário definiu como obrigatórios os campos em inglês `brand`, `url`, `price_full`, `price_discount`, `product_name`, `product_description`, `composition`, `available_colors`, `available_sizes`, `product_code`, `category`, `rating` e `review_count`. Depois travou que `product_code` é o código comercial visível na PDP/listagem e que, quando um campo obrigatório não existir na fonte, o produto deve permanecer válido com `null`/blank.

---

## Escopo do SQLite / fronteira da phase

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite agora | Criar base analítica e primeira persistência real na Phase 37 | |
| Adiar SQLite | Manter a ideia para depois, aceitando retrabalho futuro | |
| Sem SQLite no projeto | Remover totalmente SQLite e qualquer dependência desse banco | ✓ |

**User's choice:** Sem SQLite no projeto.
**Notes:** O usuário explicou que o objetivo real da phase é apenas fazer todas as engines extraírem as mesmas informações e disponibilizarem isso no Excel. Com isso, também rejeitou relatório de cobertura e pediu para manter o comportamento atual do sistema "exatamente como está hoje", mudando apenas a padronização das extrações e das colunas exportadas.

---

## Claude's Discretion

- Escolher a melhor fronteira técnica para aplicar o mapeamento/aliasing dos campos canônicos, preservando compatibilidade com o código atual.

## Deferred Ideas

- Nenhuma. SQLite e relatório de cobertura foram removidos do escopo, não deferidos.
