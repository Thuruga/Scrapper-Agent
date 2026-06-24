---
phase: 33
slug: frete-via-checkout-nos-sites-vtex
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-24
---

# Phase 33 — UI Design Contract

> Visual and interaction contract for the VTEX shipping experience in brand search. Extends the current React/CSS system; no new component library.

---

## Experience Goal

The operator always sees which CEP drives the quote, receives all valid home-delivery options inside each VTEX product card, and can distinguish free shipping, no delivery for the CEP, and a temporary technical failure without losing the product result.

The product price and every freight price remain visually separate. This surface must not present a summed “preço total” or emphasize `landed_price`.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Existing repository CSS; no shadcn |
| Preset | Not applicable |
| Component library | Existing `GlassCard`, form controls, product cards, status banners |
| Icon library | `lucide-react` (`MapPin`, `Truck`, `AlertTriangle`, `CheckCircle2`) |
| Font | Inter with `system-ui, sans-serif` fallback |

New UI must reuse `frontend/src/App.css` variables: `--bg-color`, `--card-bg`, `--primary`, `--text-main`, `--text-muted`, `--success`, `--warning`, `--error`, and `--border`. Do not introduce hardcoded replacements for an existing semantic token.

---

## Component Contract

### CEP field

- Replace label `CEP (Opcional)` with `CEP de entrega`.
- Prefix the existing input with `MapPin` at 20px, matching the search icon treatment.
- Initialize with the visible backend `DEFAULT_CEP`; never apply a hidden destination.
- Preserve the current `00000-000` mask and eight-digit maximum.
- Under the normal field, show helper copy: `Usado para calcular o frete automaticamente.`
- On invalid/incomplete submit or export:
  - keep the query and all other form state unchanged;
  - focus the CEP input;
  - set `aria-invalid="true"` and `aria-describedby`;
  - render inline error `Informe um CEP válido com 8 dígitos.`;
  - use an error border/ring and an `AlertTriangle` icon;
  - do not send the request.
- A default-config load that resolves late must not overwrite a CEP the user already edited.
- The edited CEP remains in the module-scoped search store for the session and resets to the default after reload.

### Shipping section inside a product card

Place a compact shipping block after stock availability inside `.product-details`:

1. Add a 1px `--border` divider with 12px top margin and 12px top padding.
2. Header row: `Truck` at 14px and label `Entrega para {CEP}`.
3. Render every `shipping_options` item as a two-column row:
   - left: service name, then estimate below;
   - right: freight price, right aligned;
   - no controls inside the row; the existing card link remains the only card action.
4. Order rows exactly as returned by the backend: lowest price first, shortest estimate as tie-breaker.
5. Use a 1px internal divider between options except after the last item.
6. Old history records without `shipping_options` fall back to the existing single `shipping` display.

### Delivery option row

- Service name: body-small, semibold, `--text-main`; use `Entrega` only if the backend name is empty.
- Estimate: label-small, `--text-muted`.
- Business-day copy: `Até {N} dias úteis`.
- Other official VTEX units must remain truthful: `Até {N} dias`, `Até {N} horas`, or `Até {N} minutos`.
- Paid freight: `R$ 19,90` using body-small, semibold, `--text-main`.
- Free freight: text `Frete Grátis`, semibold, `--success`, preceded by `CheckCircle2`; never show only `R$ 0,00`.
- Keep paid alternatives visible when a free option exists.
- Pickup/retirada must never be rendered.

### Product and freight price separation

- Keep `.price-current` exclusively for the product price.
- Shipping rows live in their own labeled section and use smaller typography than the product price.
- Do not display `Produto + Frete`, `Preço total`, `Valor final`, or `landed_price` in this brand-search surface.
- Do not change the separate SKU/marketplace page in this phase; global standardization remains a follow-up.

---

## State Matrix

| State | Visual treatment | Required copy |
|-------|------------------|---------------|
| Default CEP loading | Input disabled only until initialization completes; preserve layout | `Carregando CEP padrão…` as helper text |
| Available options | Standard shipping section with one row per home-delivery SLA | `Entrega para {CEP}` |
| Free option | Green icon and text within its row; paid rows remain neutral | `Frete Grátis` |
| No home delivery | Neutral/muted row with `MapPin`; no red error styling | `Entrega indisponível para este CEP` |
| Temporary failure after retry | Amber `AlertTriangle`; product card remains usable | `Frete temporariamente indisponível` |
| Invalid CEP | Error border, icon, helper, focused field; search blocked | `Informe um CEP válido com 8 dígitos.` |
| Legacy result | Existing single-shipping row; no blank block or crash | Existing `shipping.status` and estimate |

No state may use color alone. Every state requires the exact text above and an appropriate icon where specified.

---

## Spacing Scale

Declared values are multiples of 4 and align with the existing CSS:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon/text gaps, estimate-to-name gap |
| sm | 8px | Option row gaps, compact horizontal spacing |
| md | 16px | Card inner spacing and section rhythm |
| lg | 24px | Major form/card group gaps |
| xl | 32px | Page section separation |
| 2xl | 48px | Reserved for page-level breaks |
| 3xl | 64px | Reserved for major desktop layout gaps |

Exceptions: existing `.search-input-wrapper` uses 12px radius and 54px height; existing `.product-card` uses 15px radius. Preserve these established values instead of normalizing them in this phase.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Product price | 20px | 800 | 1.2 |
| Body | 15px | 500 | 1.4 |
| Shipping service / price | 13px | 600 | 1.35 |
| Shipping estimate / helper | 12px | 500 | 1.4 |
| Field label | 11.5px | 800 | 1.2 |

The shipping section must never compete typographically with the product price. Use tabular numeric alignment where supported (`font-variant-numeric: tabular-nums`) for freight prices.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0f172a` / `--bg-color` | Page background |
| Secondary (30%) | `rgba(30, 41, 59, 0.5)` / `--card-bg` | Product cards and glass surfaces |
| Accent (10%) | `#6366f1` / `--primary` | Product price, focus ring, primary CTA |
| Success | `#10b981` / `--success` | `Frete Grátis` only in shipping rows |
| Warning | `#f59e0b` / `--warning` | Temporary freight failure |
| Destructive | `#ef4444` / `--error` | Invalid CEP only; not “no delivery” |

Accent is reserved for primary actions, focus, active navigation, and product price. Shipping prices use `--text-main`; only free shipping uses success green.

---

## Responsive Contract

- At widths up to 980px, preserve the existing one-column search-form layout.
- Shipping option rows remain two columns while price and service fit; the service column is `minmax(0, 1fr)` and price is `max-content`.
- At widths up to 640px, keep freight price right aligned but allow service name and estimate to wrap; never horizontally scroll the product card.
- All exact state copy may wrap to two lines; do not truncate error or unavailability messages.
- Maintain minimum 44px height for form controls and buttons. Shipping rows are informational and need no touch target.

---

## Motion and Interaction

- Preserve current 0.2s focus/hover transitions.
- Do not add accordion, carousel, tooltip-only disclosure, skeleton animation, or per-option interaction.
- Do not animate reordering of delivery options.
- Respect `prefers-reduced-motion` through the existing app behavior; no new essential motion.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| CEP label | `CEP de entrega` |
| CEP helper | `Usado para calcular o frete automaticamente.` |
| CEP loading | `Carregando CEP padrão…` |
| CEP validation | `Informe um CEP válido com 8 dígitos.` |
| Shipping heading | `Entrega para {CEP}` |
| Free option | `Frete Grátis` |
| No delivery | `Entrega indisponível para este CEP` |
| Temporary failure | `Frete temporariamente indisponível` |
| Business-day estimate | `Até {N} dias úteis` |
| Calendar-day estimate | `Até {N} dias` |
| Hour estimate | `Até {N} horas` |
| Minute estimate | `Até {N} minutos` |
| Primary CTA | `Comparar` (unchanged) |

Avoid `Frete a calcular`, `Indisponível` without explanation, and generic `Erro no frete`.

---

## Accessibility Contract

- The CEP input has a programmatic label, input mode `numeric`, autocomplete `postal-code`, and invalid-state association through `aria-describedby`.
- Inline validation uses `role="alert"` or an `aria-live="polite"` container.
- Shipping section uses a heading/label and semantic list (`ul`/`li`) or equivalent accessible grouping.
- Icons are decorative when adjacent text conveys the state (`aria-hidden="true"`).
- Success/warning/error states include text, not color alone.
- Preserve visible keyboard focus using the existing primary focus ring.
- The entire product card remains an external link; shipping rows contain no nested buttons or links.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | None | Not applicable |
| Third-party registries | None | No registry code allowed for this phase |

No package installation is required. Reuse existing React, Zustand, Lucide, Sonner, and CSS.

---

## Acceptance Checklist

- [x] CEP destination is visible, editable, session-scoped, and never silently applied.
- [x] Invalid CEP blocks both search and export with accessible inline feedback.
- [x] Every valid home-delivery option appears; pickup never appears.
- [x] Options are ordered by price then estimate and preserve official VTEX units.
- [x] Free, unavailable-for-CEP, and temporary-failure states are textually distinct.
- [x] Product price and freight remain visually separate; no total is displayed.
- [x] Legacy history without `shipping_options` has a defined fallback.
- [x] Desktop, tablet, and mobile layout behavior is specified.
- [x] No new design system or registry dependency is introduced.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS — all user-visible states have exact Portuguese copy and recovery meaning.
- [x] Dimension 2 Visuals: PASS — component hierarchy, states, responsive behavior, motion, and accessibility are defined.
- [x] Dimension 3 Color: PASS — existing semantic tokens are reused and state colors have explicit boundaries.
- [x] Dimension 4 Typography: PASS — sizes, weights, hierarchy, and numeric alignment are specified.
- [x] Dimension 5 Spacing: PASS — 4px scale plus documented legacy exceptions.
- [x] Dimension 6 Registry Safety: PASS — no registry or new package usage.

**Approval:** approved 2026-06-24
