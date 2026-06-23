# Phase 27: Histórico Completo + Gestão de Marcas na UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-20
**Phase:** 27-hist-rico-completo-gest-o-de-marcas-na-ui
**Areas discussed:** Superfície do histórico, Conteúdo/ações da entrada, Comportamento ao reabrir, Layout gestão de marcas

---

## Superfície do histórico

| Option | Description | Selected |
|--------|-------------|----------|
| Aba 'Histórico' no sidebar | Aba dedicada com lista única de TODAS as buscas (comparativa + SKU misturadas). | |
| Painel/drawer nas páginas de busca | Painel lateral dentro de SearchPage/CrossMarketplacePage. | |
| Seções separadas por tipo | Histórico de comparativas na aba de busca por marca; histórico de SKU na aba de SKU. | ✓ |

**User's choice:** Seções separadas por tipo
**Notes:** Cada aba de busca exibe seu próprio histórico; a "aba correta" do critério #2 do roadmap é inerente à seccionação.

---

## Conteúdo/ações da entrada

| Option | Description | Selected |
|--------|-------------|----------|
| Rótulo + badge tipo + data + status | Ex.: 'Reserva, Aramis · 3 marcas' [Comparativa] · 18/06 · ✓Concluída. | ✓ |
| Mínimo: rótulo + data | Só texto da busca e quando foi feita. | |
| Detalhado + contagem de resultados | Recomendado + nº de produtos encontrados. | |

**User's choice:** Rótulo + badge tipo + data + status
**Notes:** Comparativa rotulada por marcas/termo; SKU mantém 'SKU: {query}'. Ações: reabrir (clique) + excluir.

---

## Comportamento ao reabrir

| Option | Description | Selected |
|--------|-------------|----------|
| Trocar de aba + reexibir automático | Leva à aba correta e reexibe sem raspar, via preloadedJobId propagado por App.tsx. | ✓ |
| Abrir em modal/overlay | Mostra os resultados salvos num overlay sem sair da aba. | |

**User's choice:** Trocar de aba + reexibir automático

| Option (sobrescrever) | Description | Selected |
|--------|-------------|----------|
| Sobrescreve direto | Substitui o conteúdo da aba; risco baixo pois toda busca fica salva (HIST-01). | ✓ |
| Pede confirmação | Aviso antes de substituir busca em andamento/exibida. | |

**User's choice:** Sobrescreve direto

| Option (entradas-limite) | Description | Selected |
|--------|-------------|----------|
| Só COMPLETED reabre | FAILED com badge de erro (não reabre); PENDING com indicador 'em andamento'. | ✓ |
| Todas clicáveis | FAILED mostra erro salvo; PENDING tenta carregar. | |
| Esconder não-concluídas | Só lista COMPLETED. | |

**User's choice:** Só COMPLETED reabre

---

## Layout gestão de marcas

| Option | Description | Selected |
|--------|-------------|----------|
| Estender lista da aba 'Marcas' c/ toggle por linha | Reaproveita SettingsPage; mantém form de adicionar, toggle ativo/inativo + excluir por linha. | ✓ |
| Tabela com colunas | Substitui a lista por tabela (nome, domínio, engine, status, ações). | |
| Modal por marca | Lista enxuta; clique abre modal com todos os campos + toggle. | |

**User's choice:** Estender lista da aba 'Marcas' c/ toggle por linha

| Option (inativas) | Description | Selected |
|--------|-------------|----------|
| Mostrar todas c/ distinção visual | Ativas e inativas juntas; inativas com badge/opacidade. GET /brands/ já retorna inativas. | ✓ |
| Só ativas + filtro 'mostrar inativas' | Padrão mostra ativas; toggle revela inativas. | |
| Duas listas separadas | Seções 'Ativas' e 'Inativas'. | |

**User's choice:** Mostrar todas c/ distinção visual

| Option (desativar/excluir) | Description | Selected |
|--------|-------------|----------|
| Toggle reversível + excluir separado c/ confirmação | Toggle = is_active (PATCH); excluir = DELETE permanente com confirmação. | ✓ |
| Só desativar (sem excluir na UI) | Exclusão permanente fica fora da interface. | |
| Ambos sem confirmação | Toggle e excluir agem direto. | |

**User's choice:** Toggle reversível + excluir separado c/ confirmação

---

## Claude's Discretion

- Posição/forma exata da seção de histórico dentro de cada página.
- Formato preciso do rótulo da comparativa e estilo do badge.
- Estado vazio do histórico; limite/paginação de itens.
- Mecânica de propagação do job ao reabrir (estado em App.tsx vs estado local da página).
- Adição da chamada PATCH no client.ts.

## Deferred Ideas

- Nenhum scope creep surgiu na discussão.
- **Reviewed todo (não dobrado):** "Reforçar discriminação de modelo" — domínio de relevância de busca (Phase 23), fora do escopo desta fase.
