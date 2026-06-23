# Phase 34: Extração de Banners Desktop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 34-extração-de-banners-desktop
**Areas discussed:** Disparo e seleção, Histórico local, Arquivo preservado, Revisão e aprovação

---

## Disparo e seleção

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Superfície de execução | Dashboard com CLI de apoio; somente terminal | Dashboard para o usuário final |
| Local da feature | Aba dedicada Banners; tela Marcas | Aba dedicada Banners |
| Seleção de marcas | Todas sempre; todas por padrão com seleção livre | Todas por padrão, usuário marca/desmarca |
| Feedback | Progresso e resultados incrementais; somente resultado final | Progresso por marca e resultados incrementais |
| Parar | Cancelar imediatamente; terminar marca atual | Cancelar imediatamente, preservar concluídos na sessão |

**User's choice:** Botão em aba dedicada, seguindo a seleção da busca comparativa, com progresso incremental, aviso final e ação Parar.
**Notes:** Parar cancela a marca em processamento e marca as restantes como canceladas; resultados já concluídos permanecem visíveis na sessão.

---

## Histórico local

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Preservação | Execuções datadas; substituir última | Preservar execuções anteriores |
| Retenção | 30 dias; últimas N; sem limpeza | 30 dias + exclusão manual |
| Reabertura | Abrir resultados salvos; somente resumo | Abrir galeria sem nova coleta |
| Canceladas/parciais | Manter com status; não manter | Não entram no histórico |

**User's choice:** Reutilizar o padrão do histórico de buscas, preservando apenas execuções completas por 30 dias.
**Notes:** O usuário pode excluir manualmente; resultados cancelados/parciais não são persistidos no histórico.

---

## Arquivo preservado

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Resolução | Maior desktop; variante renderizada | Maior resolução desktop |
| Nome | Original; ordem+descrição+hash; ordem+descrição+marca | Ordem + descrição + marca |
| Formato | Preservar original; converter | Preservar original |
| Duplicatas | Cópia por execução; deduplicar por SHA-256 | Deduplicação interna |

**User's choice:** Maior resolução desktop, formato original e nome legível terminando na marca.
**Notes:** Exemplo `01-sale-inverno-aramis.webp`; SHA-256 fica apenas nos metadados e na deduplicação física.

---

## Revisão e aprovação

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Gate | Aprovação explícita; automática | Aprovação explícita |
| Granularidade | Execução inteira; por banner | Por banner, todos selecionados inicialmente |
| Desmarcados | Manter como não aprovados; remover | Remover da execução final |
| Alteração posterior | Aprovação definitiva; editável | Aprovação definitiva |

**User's choice:** Revisão explícita na galeria; desmarcar falsos positivos e aprovar os restantes.
**Notes:** O histórico final mostra somente aprovados. Uma correção posterior exige nova extração.

---

## Claude's Discretion

- Estrutura técnica dos serviços/endpoints e detalhes visuais consistentes com os padrões existentes.
- Retry, timeouts, concorrência e formato interno do armazenamento content-addressed.

## Deferred Ideas

- Phase 35: conexão SharePoint real usando uma pasta temporária/fictícia até o caminho definitivo ser informado.

