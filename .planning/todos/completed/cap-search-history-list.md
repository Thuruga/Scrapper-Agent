---
created: 2026-06-20
area: frontend + backend
source: 27-VERIFICATION.md (non-blocking follow-up)
priority: low
status: resolved
resolved: 2026-07-06
---

**Resolvido em 2026-07-06.** `SearchHistoryService.list_jobs()` agora aceita
`limit` (default 50, `None` retorna tudo); `GET /history` expõe `limit` via
query param (1-500). `HistoryList`/`HistoryPanelBody` no frontend ganharam
botão "Mostrar mais antigas" que aumenta o limite sob demanda. 4 novos testes
em `test_search_history_comparative.py`; suite completa e build do frontend
verdes.

# Cap / paginate the search history list

`SearchHistoryService.list_jobs()` returns ALL records (only pruned >30 days at startup), and the `HistoryList` component fetches + renders the full list on each refresh. Low impact today (single-user tool; the panel is collapsed by default so DOM nodes aren't inserted until expanded), but it grows unbounded over a 30-day window.

**Proposed:** add a server-side cap in `list_jobs()` (e.g. top-50 most recent) and a client-side "mostrar mais antigas" expansion in `HistoryList`. Surfaced by the Phase 27 adversarial verification as a warning; deferred to avoid scope creep.
