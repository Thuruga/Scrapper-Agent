---
phase: 34
slug: extra-o-de-banners-desktop
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-23
---

# Phase 34 — UI Design Contract

> Visual and interaction contract for the user-facing Banners workflow. This phase extends the existing hand-rolled glass UI; it introduces no component library or package.

## Design System

| Property | Value |
|----------|-------|
| Tool | none — existing React JSX + `frontend/src/App.css` |
| Preset | not applicable |
| Component library | existing custom `GlassCard`, buttons, chips, badges, progress bars |
| Icon library | `lucide-react` already installed |
| Font | `Outfit`, sans-serif inherited from `frontend/src/index.css` |

Reusable assets are mandatory: `.glass-card`, `.btn`, `.btn-primary`, `.btn-outline`, `.brand-filter-panel`, `.brand-chip`, `.progress-bar-large`, `.progress-fill-large`, `.monitor-badge`, `.empty-state`, `.status-banner`, and existing sidebar/nav patterns. Do not introduce shadcn, Tailwind, a second token layer, or a new font.

## Information Architecture

Add one sidebar item and one page:

- **Sidebar label:** `Banners`
- **Icon:** `Images` from `lucide-react`
- **Tab key:** `banners`
- **Page component:** `BannersPage`

Page order:

1. extraction/brand-selection `GlassCard`;
2. active job progress `GlassCard` when a job exists;
3. current-run gallery and approval toolbar when candidates exist;
4. completed banner history, collapsed by default.

## Component and Interaction Contract

### A. Extraction card

Header: `Extração de banners`.

Body:

- explanatory copy: `Selecione as marcas e extraia todos os banners desktop do carrossel principal.`
- reuse the comparative search brand grid and `.brand-chip` behavior;
- all active brands selected on first entry;
- actions `Selecionar todas` and `Desmarcar todas` use `.btn-sm .btn-outline`;
- selected count copy: `{N} de {total} marcas selecionadas`.

Primary action:

- idle: `Extrair banners` with `Play` or `Images` icon;
- disabled when zero brands are selected;
- while running, replace with destructive-outline `Parar extração` using `Square` icon;
- Stop acts immediately without a confirmation dialog.

### B. Progress card

Header: `Extração em andamento`.

- overall line: `{completed} de {total} marcas processadas`;
- reuse `.progress-bar-large` with numeric percent visible in text;
- one compact row per selected brand with name, status badge, and discovered image count;
- statuses: `Aguardando`, `Extraindo`, `Concluída`, `Falhou`, `Cancelada`;
- completed brand results are inserted into the gallery immediately;
- terminal success uses toast `Extração concluída. Revise os banners antes de aprovar.`;
- cancelled/partial run uses inline info banner, remains visible only in the current session, and is not added to history.

Status is communicated by text/icon as well as color.

### C. Review gallery

Header: `Revisar banners` plus selected count `{selected} de {total} selecionados`.

Grid:

- desktop: `repeat(auto-fill, minmax(320px, 1fr))`;
- card preview uses the complete image with `object-fit: contain`, never a crop;
- preview background uses existing dark surface; minimum preview aspect ratio `16 / 7`;
- checkbox control is top-left and the entire card toggles selection;
- all cards selected initially;
- selected card gets `--primary` border and a check icon; unselected card gets 0.55 opacity;
- metadata below preview: brand, filename, pixel dimensions, format, slide order;
- secondary link `Abrir original` opens the stored asset in a new tab;
- viewport screenshot is available through `Ver primeira tela` per brand for diagnostic comparison.

Toolbar actions:

- `Selecionar todos` and `Desmarcar todos` as outline buttons;
- primary CTA `Aprovar {N} banners`;
- approval confirmation: `Aprovar {N} banners? Os itens desmarcados serão removidos e esta aprovação não poderá ser alterada.`;
- after approval, only selected items remain and the run becomes read-only/history-visible;
- zero selected disables approval and shows `Selecione ao menos um banner para aprovar.`.

### D. Banner history

Reuse the established `HistoryList` interaction in a banner-specific component or parameterization.

- section heading: `Histórico de banners`;
- collapsed by default with count badge;
- newest first;
- each row shows date/time, number of approved banners, number of brands, and `Concluída` status;
- clicking reopens the saved gallery without starting a new extraction;
- delete icon with confirmation: `Excluir esta extração do histórico? Os arquivos sem outras referências também serão removidos.`;
- automatic 30-day retention is backend behavior and does not need UI configuration;
- cancelled, partial, failed, or awaiting-review runs do not appear here.

## States Summary

| Surface | Empty | Loading/running | Error/partial | Success/review |
|---------|-------|-----------------|---------------|----------------|
| Brand selection | active brands unavailable: `Nenhuma marca ativa disponível` | action disabled while active job runs | load error via status banner | all active selected initially |
| Progress | hidden with no job | progress bar + per-brand rows | explicit failed/cancelled badges | completed rows with image counts |
| Gallery | `Nenhum banner encontrado nesta execução` | cards append incrementally | failed brand does not remove completed cards | all candidates selected for review |
| History | `Nenhuma extração aprovada ainda` | `Carregando histórico…` + spinner | toast and keep existing list | rows reopen immutable approved gallery |

## Spacing Scale

Use the existing 4px-derived scale only.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | status/icon micro gaps |
| sm | 8px | card metadata and compact actions |
| md | 16px | gallery/card gaps and row padding |
| lg | 24px | GlassCard padding and section gap |
| xl | 32px | page-level section separation |

Exceptions: none.

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14–15px | 400 | 1.5 |
| Label/meta | 12–13px | 500–700 | 1.4 |
| Card heading | 16px | 700 | 1.25 |
| Page heading | existing page title size | 700–800 | existing |

Do not introduce new typography tokens.

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant | `--bg-color` / `--bg-dark` | page background |
| Secondary | `--card-bg`, `--sidebar-bg` | cards and rows |
| Accent | `--primary` #6366f1 | primary CTA, selected brands/cards, active progress |
| Secondary accent | `--accent` #06b6d4 | informative metadata only |
| Success | `--success` #10b981 | completed/approved |
| Destructive | `--error` #ef4444 | stop, failure, delete |
| Warning | existing `--warning` | awaiting review/partial |

Accent is reserved for selection, the active job, and approval CTA. Status cannot rely on color alone.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Page/sidebar | `Banners` |
| Primary CTA | `Extrair banners` |
| Stop CTA | `Parar extração` |
| Review CTA | `Aprovar {N} banners` |
| Completed toast | `Extração concluída. Revise os banners antes de aprovar.` |
| Approved toast | `{N} banners aprovados e adicionados ao histórico.` |
| Cancelled info | `Extração interrompida. Resultados parciais não serão salvos no histórico.` |
| Empty history heading | `Nenhuma extração aprovada ainda` |
| Empty history body | `As extrações concluídas e aprovadas aparecerão aqui por 30 dias.` |
| Approval confirmation | `Aprovar {N} banners? Os itens desmarcados serão removidos e esta aprovação não poderá ser alterada.` |
| Delete confirmation | `Excluir esta extração do histórico? Os arquivos sem outras referências também serão removidos.` |

## Accessibility Basics

- brand chips and banner cards are real buttons/checkbox-backed controls with visible focus;
- icon-only actions have Portuguese `aria-label` text;
- progress uses `aria-valuenow`, `aria-valuemin`, and `aria-valuemax`;
- status has label and icon, never color only;
- gallery images use alt from extraction, falling back to `{marca} — banner {ordem}`;
- keyboard users can toggle cards with Space and approve via the primary button;
- dialogs focus the safe action first and return focus to the invoking control.

## Responsive Safety

Banner **extraction** remains desktop-only. The dashboard surface may collapse to one gallery column under 768px so it does not break the existing responsive shell; this does not add mobile banner extraction.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| none | none | not applicable |

No packages or registry blocks are added.

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS — concrete labels, terminal states, confirmations, and empty states defined.
- [x] Dimension 2 Visuals: PASS — page hierarchy, cards, progress, selection, history, and responsive fallback specified.
- [x] Dimension 3 Color: PASS — existing tokens only; status includes text/icon.
- [x] Dimension 4 Typography: PASS — inherited scale and roles explicitly bounded.
- [x] Dimension 5 Spacing: PASS — existing 4px scale, no exceptions.
- [x] Dimension 6 Registry Safety: PASS — no external blocks/packages.

**Approval:** approved 2026-06-23

