# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v4.0 — Paridade de Dados, Cobertura Total de Frete & Inteligência Competitiva

**Shipped:** 2026-07-08
**Phases:** 9 (37-45) | **Plans:** 32 | **Tasks:** 48

### What Was Built

- Canonical, aditive attribute vocabulary shared by every engine/parser (VTEX, Wake, SFCC, Zara, marketplaces), with fixed canonical Excel export columns across comparative/category surfaces.
- Full brand coverage: Hugo Boss category scanning (VTEX-IO DOM-tile strategy), Zara onboarded (GO after an initial NO-GO reversal), Lacoste removed from active search.
- URL-only brand onboarding + idempotent "add to monitoring" from all three search surfaces, with a mid-phase UX rework (identify-first flow) based on operator feedback.
- Shipping parity: non-VTEX abstraction (`BaseShipping`), all three marketplaces (Mercado Livre, Netshoes, Amazon), and an on-demand 5-region shipping matrix with throttle/cache.
- Competitive intelligence layer: MAP violation alerts, structured promo/payment badges, stock rupture %, 999-unit cart-probe stock depth, enhanced review/comment extraction, and an assortment (sortiment) gap-analysis cron with a dedicated dashboard.

### What Worked

- The spike-gated GO/NO-GO pattern (Zara, Lacoste) caught a real anti-bot false negative — Zara's initial NO-GO was environment-dependent, and the gate structure made it safe to re-test live and reverse the verdict without having built throwaway engine code first.
- Additive-only schema changes (canonical attribute aliasing, `promotions` field, `shipping_options`) meant zero regressions while adding significant new surface area — raw fields were never overwritten, only extended.
- Guard-rail discipline held: cart-probe (STOCK-02) and the regional shipping matrix (FRET-09) were both designed up front to be on-demand/throttled/never-inline, so no live-search performance regression was introduced by either.

### What Was Inefficient

- REQUIREMENTS.md's traceability table and ROADMAP.md's Progress table drifted out of sync with actual phase completion (PARID-01..04 and FRET-07 stayed "Pending" after their phases shipped; UX-03/04 stayed "Partial"; Phase 37's roadmap checkbox stayed unchecked). None of this was caught until milestone close, requiring a manual reconciliation pass against phase SUMMARY/VERIFICATION files.
- When Zara's spike verdict flipped from NO-GO to GO on 2026-07-01, the correction only propagated to the completed-todo file — REQUIREMENTS.md, MILESTONES.md-in-progress notes, and the milestone accomplishments list all still said "deferred/NO-GO" a week later at milestone close.
- ROADMAP.md's "Phase Details" section had copy-paste corruption (Phase 39 and Phase 43 both listed Phase 45's plan filenames instead of their own), which would have propagated into the archive had it not been caught during the close.
- Phase 40's UX-03 rework left a `checkpoint:human-verify` gate open with no `40-HUMAN-UAT.md` ever filed, unlike every other phase that had pending UAT — it was missed by the batch UAT confirmation that covered phases 33/37/38/42/44.

### Patterns Established

- "Identify-first" onboarding: instead of a standalone brand-add-by-URL form, paste-a-product-URL-and-auto-identify lives inside the primary action surface (the monitor "add new" flow) with manual-select fallback.
- On-demand + never-inline for anything with a per-call cost (cart-probe, regional shipping matrix): guarded explicitly at the call site, covered by a regression test, never triggered from a live search/scan path.
- When a spike verdict changes, the reversal gets logged as an update to the *same* todo/decision record (not a new one) so the history of "why we changed our mind" stays attached to the original claim.

### Key Lessons

1. Update REQUIREMENTS.md traceability (and tick the ROADMAP.md phase checkbox) as part of each phase's own closing steps, not deferred to milestone close — stale status labels accumulate silently and all have to be manually reconciled against phase artifacts in one expensive pass at the end.
2. When a gate verdict reverses (NO-GO → GO or vice versa), grep every doc that recorded the original verdict (requirements traceability, milestone accomplishments draft, PROJECT.md backlog) before closing the milestone — a single corrected file is not enough if the original claim was copied into three others.
3. Batch UAT confirmation sweeps (confirming several phases' pending manual checks in one sitting) need an explicit checklist of *which* phases have open `checkpoint:human-verify` gates, not just "confirm the ones I remember" — Phase 40's UX-03 rework was missed this way for over a week.

### Cost Observations

- Sessions: not tracked per-session in this repo's planning artifacts.
- Model mix: not tracked.
- Notable: the milestone-close audit (this session) surfaced 3 real doc-accuracy gaps (stale traceability, Zara verdict reversal not propagated, ROADMAP.md copy-paste corruption) that automated `roadmap.analyze`/`audit-open` tooling did not catch — they only became visible by reading phase-level SUMMARY/VERIFICATION files directly.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v4.0 | — | 9 | First milestone closed with a full manual reconciliation of REQUIREMENTS.md traceability against phase artifacts at close time (see Key Lessons). |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|---------------------|
| v4.0 | 500+ backend (exact count not centrally tracked) | not measured | SQLite (stdlib) for analytics data (Phase 37) |

### Top Lessons (Verified Across Milestones)

1. Keep requirement traceability and roadmap checkboxes updated at phase-close time, not milestone-close time.
