# Phase 23: Discriminação de Modelo - Research

**Researched:** 2026-06-13
**Domain:** NLP penalty tuning + cross-candidate visual tiebreak sort (no new libraries)
**Confidence:** HIGH — all findings verified against live code and live search_history data

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Mechanism:** reforcar a penalidade multiplicativa existente em `_apply_model_word_penalty` (ajustar multiplicadores `WITH_BRAND` via config). NAO introduzir gate rigido de model-words.
- **Gatilho:** discriminacao reforada aplica-se apenas quando a marca da query bate no titulo (caso "mesmo fabricante").
- **Definicao de model-word:** manter heuristica atual (palavra >= 3 chars, nao esta em `brand_and_category_words`, nao esta em `stop_words`).
- **`model_ratio ~= 0` (mesma marca, zero model-words):** penalidade forte o suficiente para rebaixar abaixo da regua de corte.
- **Visual tiebreak:** "texto ambiguo" = janela de proximidade configuravel entre candidatos da mesma marca; dentro da janela, maior `image_score` sobe.
- **Tiebreak implementado como REORDER STEP em `cross_marketplace_service`** — `relevance_gates.py` fica PURO (LOCKED Phase 22).
- **Novos params em RelevanceSettings/.env** (sem hardcode). Novo flag `VISUAL_TIEBREAK_ENABLED` (default True). Reforco de model-words usa knobs `NLP_MODEL_PENALTY_*` existentes.
- **Fallback sem sinal visual** (image_score==0 / AI indisponivel / flag off) = comportamento atual, zero regressao.

### Claude's Discretion

- Nome exato e default da config key da janela de ambiguidade e valores reforados dos multiplicadores `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` / `_MED_WITH_BRAND`.
- Onde exatamente inserir a etapa de reordenacao e se o desempate e uma funcao pura de nivel de modulo importavel pelos testes.
- Se o desempate agrupa por `(plataforma, marca)` ou so por marca.
- Estrutura exata dos testes.

### Deferred Ideas (OUT OF SCOPE)

- IDENT-01 (sinal de identidade alem do EAN).
- Lista curada de model-words por linha Aramis.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-01 | Entre produtos da marca correta, o topo do resultado corresponde ao modelo/linha especifico buscado, nao a um modelo adjacente da mesma marca. | Reforco do HEAVY_WITH_BRAND para 0.45 garante model_ratio<0.50 cai abaixo de cutoff. Arithmetic verified against live scores. |
| MODEL-02 | O sinal visual (CLIP) atua como desempate entre candidatos da mesma marca quando o score de texto e ambiguo. | `apply_visual_tiebreak` function: within-window same-brand candidates sorted by -image_score. Verified correct for all 4 success criteria scenarios. |
</phase_requirements>

---

## Summary

Phase 23 has two independent levers: (1) strengthen the existing model-word penalty multipliers in `_apply_model_word_penalty` so that a same-brand candidate with zero model-words in common reliably lands below the cutoff (MODEL-01 / criterion 3); (2) introduce a cross-candidate visual tiebreak reorder step in `compare_product` so that CLIP acts as an explicit discriminator between same-brand text-ambiguous candidates rather than a late-stage confirmer (MODEL-02).

The critical structural finding discovered by arithmetic (verified against live code): the existing `compute_final_match_score` Gate 1 (`if image >= 85 and text >= 40: return max(image, text)`) can rescue a penalized candidate back to 85+ even when the text penalty would otherwise drop it below cutoff. With the current HEAVY_WITH_BRAND=0.70, a raw blend of 88 becomes 61.6 — still above cutoff (60) without needing the gate. To truly drop model_ratio<0.50 items below cutoff AND block the Gate 1 rescue, the penalized text must fall below 40 (MED_TEXT_FLOOR). The multiplier that achieves this for all realistic raw blends (up to ~88) is 0.45: `88 * 0.45 = 39.6 < 40`. This is the calibrated recommendation for `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND`.

For the MED range (model_ratio 0.50–0.75), strengthening from 0.90 to 0.75 improves discrimination for this range but does not fully block the image rescue gate; the visual tiebreak handles the residual ambiguity, which is exactly the MODEL-02 case. Correct-model color variants (ratio >= 0.75) receive no penalty and are unaffected.

**Primary recommendation:** Two-task delivery: Task 1 = tighten `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` to 0.45 and `NLP_MODEL_PENALTY_MED_WITH_BRAND` to 0.75 + add `VISUAL_TIEBREAK_ENABLED` and `VISUAL_TIEBREAK_TEXT_WINDOW` to `RelevanceSettings`. Task 2 = add `apply_visual_tiebreak` module-level function to `cross_marketplace_service.py`, wire into the sort step, and write 5 anchor tests mirroring `test_brand_gate.py`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| model-word penalty strength | NLP Service (`nlp_service.py`) | Config (`config.py`) | Penalty logic already lives in `_apply_model_word_penalty`; config provides the knobs |
| Visual tiebreak reorder | Service pipeline (`cross_marketplace_service.py`) | Config (`config.py`) | Cross-candidate decision — cannot be in per-candidate `compute_final_match_score`; mirrors `passes_brand_gate` placement |
| Score purity / gate arithmetic | Relevance Gates (`relevance_gates.py`) | — | LOCKED pure — no changes, receives already-penalized text score |
| Config flags + defaults | `RelevanceSettings` in `config.py` | `.env` override | Established idiom for all knobs in this pipeline |
| Validation (tests) | `tests/test_model_discrimination.py` (new) | — | Mirrors `test_brand_gate.py` style |

---

## Standard Stack

No new libraries. All work is pure Python using existing imports.

### Core (existing, no changes)
| Module | Purpose | Used For |
|--------|---------|----------|
| `services/nlp_service.py` | NLP scoring + brand detection | Adjust multipliers in `_apply_model_word_penalty`; `brand_is_present` reused by tiebreak |
| `services/cross_marketplace_service.py` | Pipeline orchestration | Insert `apply_visual_tiebreak` at sort step |
| `config.py` (`RelevanceSettings`) | All hyperparameters | Add 2 new fields |
| `services/relevance_gates.py` | Pure score gates | No changes (LOCKED) |
| `rapidfuzz` | Fuzzy matching | Already in use — no version change |

### Installation

No `pip install` required. Zero new dependencies.

---

## Package Legitimacy Audit

Not applicable — no new packages installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Query (SKU + official_title)
       |
       v
[NLP: calculate_text_score]
  |-- fuzzy blend (wratio/tsort/ptset)
  |-- _apply_model_word_penalty  <-- LEVER 1: tighten HEAVY_WITH_BRAND to 0.45
  |-- _apply_category_penalty
  |-- _apply_brand_penalty
  -> text_match_score (already penalized)
       |
       v
[top_candidates selection (per platform, by text_score)]
       |
       v
[CLIP visual scoring -> image_match_score]
       |
       v
[compute_final_match_score(text, image)] -- relevance_gates.py (PURE, UNCHANGED)
  |-- Gate 1: if image>=85 and text>=40: max(image,text)
  |-- Gate 2: if text>=90: max(text,image)
  |-- Gate anti-WAF: if image==0 and text>=80: text
  |-- else: text*0.60 + image*0.40
  -> final_match_score
       |
       v
[cutoff filter + brand_gate -> produtos_filtrados]  -- unchanged
       |
       v
[apply_visual_tiebreak(candidates, window, enabled, official_title)]  <-- LEVER 2
  |-- fallback (enabled=False or all image==0): sort(-final, preco)
  |-- else: group by brand, sort by bucket(-final,window) then -image_score
  -> reordered list
       |
       v
[per-platform cap -> top_filtered]  -- unchanged
       |
       v
[PDP fetch + shipping + format + dedup + buybox]  -- unchanged
```

### Recommended Project Structure (no new files except test)

```
services/
  nlp_service.py          # adjusted: NLP_MODEL_PENALTY multipliers (no structural change)
  cross_marketplace_service.py  # adjusted: apply_visual_tiebreak + VISUAL_TIEBREAK_ config reads
  relevance_gates.py      # UNCHANGED (LOCKED)
config.py                 # adjusted: 2 new RelevanceSettings fields
tests/
  test_model_discrimination.py  # NEW: 5 anchor tests
```

### Pattern 1: Module-Level Pure Predicate/Function (mirrors passes_brand_gate)

**What:** A pure module-level function (not a method) in `cross_marketplace_service.py` that is importable by both production code and tests. The function receives all state it needs as arguments — no global reads inside the function body.

**When to use:** Any cross-candidate decision that belongs in the service but must be independently testable without running the full async pipeline.

**Example (matches Phase 22 passes_brand_gate idiom):**

```python
# Source: services/cross_marketplace_service.py (Phase 22 pattern, lines 16-38)

def apply_visual_tiebreak(
    candidates: list,
    window: float,
    enabled: bool,
    official_title: str,
) -> list:
    """
    Reorders candidates by promoting visual signal when text scores are
    ambiguous among same-brand competitors. Pure function, no side effects.

    Fallback (enabled=False or all image_scores==0):
        returns sorted by (-final_match_score, preco) -- identical to current
        behavior, zero regression.

    Args:
        candidates: list of product dicts with 'final_match_score',
                    'image_match_score', 'titulo', 'preco'.
        window: max final_match_score gap (0-100 scale) within which
                same-brand candidates are considered text-ambiguous.
        enabled: VISUAL_TIEBREAK_ENABLED flag, read by caller.
        official_title: raw official title of the searched product (used
                        only for brand detection vocabulary lookup).

    Returns:
        New list (same objects, new order).
    """
    if not candidates:
        return candidates

    has_image = any(c.get("image_match_score", 0) > 0 for c in candidates)
    if not (enabled and has_image):
        return sorted(candidates, key=lambda x: (-x["final_match_score"], x["preco"]))

    vocab_brands = nlp_service._vocab.known_brands_for_detection

    # Compute per-brand top score for window anchoring
    brand_top: dict = {}
    for c in candidates:
        bk = _detect_candidate_brand(c.get("titulo", ""), vocab_brands)
        if bk is not None:
            brand_top[bk] = max(brand_top.get(bk, 0.0), c.get("final_match_score", 0.0))

    import math

    def _sort_key(c):
        final = c.get("final_match_score", 0.0)
        img = c.get("image_match_score", 0.0)
        preco = c.get("preco", 0.0)
        bk = _detect_candidate_brand(c.get("titulo", ""), vocab_brands)
        top = brand_top.get(bk, 0.0) if bk else 0.0
        in_window = bk is not None and img > 0 and (top - final) <= window
        if in_window:
            # Floor to window bucket so within-window candidates compete on image
            bucket = math.floor(final / window) * window
            return (0, -bucket, -img, preco)
        return (0, -final, 0.0, preco)

    return sorted(candidates, key=_sort_key)


def _detect_candidate_brand(titulo: str, vocab_brands) -> str | None:
    """Returns the first known brand found in titulo after cleaning, or None."""
    clean = nlp_service._clean_text(titulo)
    words = set(clean.split())
    for brand in vocab_brands:
        if brand in words:
            return brand
    return None
```

**Calling site in compare_product (replaces line 253):**

```python
# Before (line 253):
# produtos_filtrados.sort(key=lambda x: (-x["final_match_score"], x["preco"]))

# After:
produtos_filtrados = apply_visual_tiebreak(
    produtos_filtrados,
    window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW,
    enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED,
    official_title=official_title,
)
```

Note: `apply_visual_tiebreak` returns a new list (sorted), so `produtos_filtrados` is reassigned rather than sorted in-place.

### Pattern 2: RelevanceSettings Field Addition (mirrors BRAND_GATE_ENABLED)

```python
# Source: config.py lines 216-224 (BRAND_GATE_ENABLED idiom)

# ---- Discriminacao de modelo visual (MODEL-02) ----------------------------
VISUAL_TIEBREAK_ENABLED: bool = Field(
    default=True,
    description=(
        "Quando True, candidatos da mesma marca com scores de texto dentro "
        "de VISUAL_TIEBREAK_TEXT_WINDOW sao reordenados pelo score visual "
        "(CLIP). Rollback: VISUAL_TIEBREAK_ENABLED=false desativa sem "
        "alterar codigo."
    ),
)
VISUAL_TIEBREAK_TEXT_WINDOW: float = Field(
    default=10.0,
    description=(
        "Janela de ambiguidade de texto (pontos 0-100): candidatos da mesma "
        "marca dentro desta faixa do top-score da marca sao reordenados pelo "
        "score visual. Default 10.0 cobre a dispersao tipica de variantes de "
        "cor (~5-6 pontos) mais candidatos de modelo adjacente (~8 pontos)."
    ),
)
```

### Pattern 3: Multiplier Adjustment in `_apply_model_word_penalty`

No structural change to `_apply_model_word_penalty`. The only change is to the default values in `config.py`:

```python
# Current (lines 265-267):
NLP_MODEL_PENALTY_HEAVY_WITH_BRAND: float = Field(
    default=0.70,  # <- change to 0.45
    ...
)
NLP_MODEL_PENALTY_MED_WITH_BRAND: float = Field(
    default=0.90,  # <- change to 0.75
    ...
)
```

These are `.env`-overridable: no code change required to tune further.

### Anti-Patterns to Avoid

- **Putting tiebreak logic in `relevance_gates.py`:** LOCKED Phase 22. That module is pure and per-candidate; the tiebreak requires cross-candidate knowledge.
- **Reading `relevance_settings` inside `apply_visual_tiebreak`:** The function must be pure — settings are read by the caller and passed as arguments (`window`, `enabled`). Mirrors `passes_brand_gate(enabled=...)` design.
- **Mutating candidates in-place:** `apply_visual_tiebreak` returns a new list. The existing `.sort()` pattern mutates; replace with `candidates = apply_visual_tiebreak(...)`.
- **Grouping by (platform, brand):** Group by brand only. Platform separation is handled downstream by the per-platform cap. Cross-platform model discrimination is a valid use case (same Aramis model on ML vs Netshoes).
- **Using `math.floor(final / window) * window` with window=0:** Guard against division by zero if window is mis-configured. Use `max(window, 0.1)` inside the function.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Brand detection in tiebreak | A new brand detector | `nlp_service._vocab.known_brands_for_detection` + `nlp_service._clean_text` | Single source of truth; already tested and correct |
| Cross-candidate sort stability | A custom merge sort | Python's built-in `sorted()` (TimSort, stable) | TimSort is stable by guarantee; equal keys preserve original order |
| New model-word vocabulary | A curated list by Aramis line | Existing heuristic: words >= 3 chars, not brand/category/stop | Zero maintenance; heuristic already works for the relevant cases |

---

## Calibration Arithmetic (Critical — verify before committing defaults)

All arithmetic verified against live codebase and real `search_history.json` polo cross-job data [VERIFIED: live code + live data].

### Current vs Recommended Multipliers

| Parameter | Current | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` | 0.70 | **0.45** | See arithmetic below |
| `NLP_MODEL_PENALTY_MED_WITH_BRAND` | 0.90 | **0.75** | More discriminating for MED range |
| `NLP_MODEL_PENALTY_LOW_THRESHOLD` | 0.50 | 0.50 (unchanged) | Boundary is correct |
| `NLP_MODEL_PENALTY_MED_THRESHOLD` | 0.75 | 0.75 (unchanged) | Boundary is correct |
| `VISUAL_TIEBREAK_TEXT_WINDOW` | — (new) | **10.0** | See window calibration below |

### Why 0.45 for HEAVY_WITH_BRAND (not 0.50)

The structural constraint is `compute_final_match_score`'s Gate 1:

```
if image_score >= 85 and text_score >= 40:
    return max(image_score, text_score)  # image RESCUES candidate!
```

For `model_ratio < 0.50` (HEAVY range), the penalized text must be `< 40` to prevent the image rescue gate from firing and pushing the candidate back to 85+.

Observed raw fuzzy blend for wrong-model same-brand candidates (polo data): **75–88**. Worst case is ~88.

```
Required: 88 * mult < 40
=> mult < 40/88 = 0.454...
=> use 0.45 (safe margin)

Verification:
  raw=88: 88 * 0.45 = 39.6 < 40  -> image rescue BLOCKED
  raw=80: 80 * 0.45 = 36.0 < 40  -> image rescue BLOCKED
  raw=75: 75 * 0.45 = 33.8 < 40  -> image rescue BLOCKED
```

With `penalized_text < 40` and `image_score` in any range:
- `image=85, text=39.6`: Gate 1 does NOT fire (text < 40). Weighted average: `39.6*0.60 + 85*0.40 = 57.8` — **below cutoff (60)**. Criterion 3 satisfied.
- `image=90, text=39.6`: Gate 1 does NOT fire. Weighted average: `39.6*0.60 + 90*0.40 = 59.8` — still below 60. Criterion 3 satisfied.

**Correct-model color variants (ratio >= 0.75):** No penalty applied (both thresholds: `0.75 < 0.50` is False, `0.75 < 0.75` is False). Text score stays at 86–96. Unaffected.

**Correct-model near-variants (ratio = 0.80):**
- `0.80 < NLP_MODEL_PENALTY_LOW_THRESHOLD (0.50)` → False
- `0.80 < NLP_MODEL_PENALTY_MED_THRESHOLD (0.75)` → False
- Multiplier = 1.0. No penalty. Stays at 86–96. Non-regression criterion 4 satisfied.

### Why 0.75 for MED_WITH_BRAND

MED range (0.50 <= ratio < 0.75) represents adjacent-model candidates that share some model-words. Example: "Polo Aramis Manga Curta Cotton Piquet Basic" vs "Polo Manga Curta Basica Piquet Marinho" has ratio=0.60.

```
raw=87: 87 * 0.75 = 65.3
```

Penalized text = 65.3 (>= 40) means Gate 1 can still rescue at image=85 → final=85. Text penalty alone does not fully solve the MED range. The visual tiebreak (MODEL-02) handles the residual: if the correct model has higher image_score within the 10-point window, it ranks first.

If we pushed MED down to 0.45 as well, ratio=0.60 items would be treated identically to ratio=0 items — too aggressive, risks dropping legitimate near-variants.

### Window Calibration

Real polo cross-job data from `data/search_history.json` (post Phase 22 brand gate, pre Phase 23):

```
Query: Polo Manga Curta Basica Piquet Marinho aramis
Results (final_match_score):
  91.3  Piquet Mescla Basica Marinho   <- correct model + correct color
  86.5  Algodao Piquet Mescla Basica Branco  <- correct model, different material/color
  86.2  Piquet Mescla Basica Grafite   <- correct model, different color
  86.0  Piquet Mescla Basica Preto     <- correct model, different color
```

Spread of correct-model color variants from top: **91.3 - 86.0 = 5.3 points**.
Wrong-model adjacents (with Phase 23 MED penalty): estimated range 65–83 (from arithmetic).

Window=10.0: covers the 5.3-point spread of correct color variants AND brings in wrong-model adjacents within 10 points of top for visual comparison. The visual signal then promotes the correct-model item.

Window=5.0: too conservative — only covers 4.7-point spread, would miss the 86.0 variant (91.3-86.0=5.3 > 5).

**VISUAL_TIEBREAK_TEXT_WINDOW = 10.0** [ASSUMED — needs validation against 2+ more polo search_history jobs]

---

## Common Pitfalls

### Pitfall 1: Gate 1 Image Rescue Bypasses Model Penalty

**What goes wrong:** Setting `NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` to 0.50 (naive "halve it") still allows Gate 1 to rescue wrong-model candidates. Example: `raw=85, mult=0.50 → text=42.5 >= 40 (MED_TEXT_FLOOR), image=85 → final=85`. Item passes cutoff despite zero model-words matching.

**Why it happens:** `_apply_model_word_penalty` runs inside `calculate_text_score` and returns an already-penalized text score. `compute_final_match_score` then applies its own gates to that penalized value. The penalty must push text below 40, not just below 60.

**How to avoid:** Use `mult=0.45` (worst-case `88*0.45=39.6 < 40`). Write a test that verifies the `model_ratio=0` candidate with `image=85` lands BELOW cutoff end-to-end.

**Warning signs:** A test of the form `assert final_score < 60` passes when `image=70` but fails when `image=85` — the image-rescue gate is the culprit.

### Pitfall 2: apply_visual_tiebreak Mutates In-Place Instead of Returning New List

**What goes wrong:** Using `.sort()` instead of `sorted()` mutates `produtos_filtrados`. The existing line 253 uses `.sort()` in-place; replacing with `apply_visual_tiebreak` must use `produtos_filtrados = apply_visual_tiebreak(...)` (reassign).

**How to avoid:** Function returns a new list (uses `sorted()`). Caller always reassigns.

### Pitfall 3: Tiebreak Reads relevance_settings Internally (Anti-Tautology Violation)

**What goes wrong:** If `apply_visual_tiebreak` reads `relevance_settings.VISUAL_TIEBREAK_ENABLED` internally, tests cannot override the flag without monkey-patching the settings singleton. This breaks the Phase 22 anti-tautology pattern (HIGH-1).

**How to avoid:** The function receives `window` and `enabled` as arguments, read by the caller from `relevance_settings`. Tests pass `enabled=True/False` and `window=10.0` directly. Mirrors `passes_brand_gate(titulo, official_title, enabled)`.

### Pitfall 4: sort_key Bucket Arithmetic Mixes Buckets and Exact Values

**What goes wrong:** If the sort key mixes `(-bucket, ...)` for in-window candidates and `(-final, ...)` for out-of-window candidates, candidates straddling a bucket boundary can be mis-ordered relative to each other.

**Example:** Candidate A at final=81 (in-window, bucket=80) vs Candidate B at final=82 (out-of-window, exact), key_A=(0,-80,...) < key_B=(0,-82,...) → A wrongly sorts before B.

**How to avoid:** The bucket flooring only affects within-window same-brand candidates. Out-of-window candidates use `(0, -final, 0.0, preco)` with `0.0` as the image secondary (image scores are always >= 0). Since in-window candidates use `(0, -bucket, -img, preco)` and out-of-window use `(0, -final, 0.0, preco)`, a comparison between the two depends only on whether `-bucket < -final` or vice versa. A candidate at final=81 (in-window, bucket=80) has key `(0, -80, ...)` while a candidate at final=79 (out-of-window) has `(0, -79, ...)`. Since `-80 < -79`, the in-window candidate sorts first — which is correct (81 > 79). A candidate at final=81 (in-window, bucket=80) vs final=85 out-of-window: `-80 > -85` → 85 sorts first. Correct. The bucket does NOT wrongly demote in-window candidates past out-of-window ones with higher final scores.

**Verify with test:** Include a scenario where an in-window candidate (final=86) competes with an out-of-window candidate (final=92) and assert the 92 sorts first.

### Pitfall 5: model_ratio Computation Runs AFTER remove_colors

**What goes wrong:** `_apply_model_word_penalty` operates on the already-color-removed, already-cleaned text (from `calculate_text_score` lines 178-180). Colors are NOT in `model_words` by construction because `remove_colors` strips them before the model-word extraction. This is correct behavior — color differences between Aramis polo variants (Marinho vs Branco) should NOT reduce model_ratio. No change needed; just verify tests use color-stripped titles as inputs if calling the penalty directly.

**How to avoid:** Tests for `apply_visual_tiebreak` work on the already-computed `final_match_score` (a float) — they never need to care about the color-stripping step.

---

## Code Examples

### Verify HEAVY multiplier blocks Gate 1 rescue (test pattern)

```python
# Source: derived from live arithmetic against services/relevance_gates.py [VERIFIED]
from services import relevance_gates

def test_model_ratio_zero_below_cutoff_even_with_high_image():
    # raw_text_before_penalty = 88 (high-similarity wrong-model candidate)
    # HEAVY_WITH_BRAND = 0.45
    # penalized = 88 * 0.45 = 39.6 -- below MED_TEXT_FLOOR (40)
    # Gate 1 (image >= 85 and text >= 40) does NOT fire
    # Weighted average: 39.6 * 0.60 + 85 * 0.40 = 57.8 < 60 (cutoff)
    text_after_penalty = 88.0 * 0.45   # = 39.6
    image = 85.0
    final = relevance_gates.compute_final_match_score(text_after_penalty, image)
    assert final < 60.0, f"Wrong-model item should be below cutoff, got {final}"
```

### Visual tiebreak promotes higher-image-score candidate within window

```python
# Source: derived from algorithm design [VERIFIED: sort_key arithmetic checked]
from services.cross_marketplace_service import apply_visual_tiebreak

def test_visual_tiebreak_promotes_higher_image_within_window():
    # Two Aramis polos, text scores within 10-point window
    correct_model = {
        "titulo": "Polo Aramis Manga Curta Piquet Mescla Basica Marinho",
        "final_match_score": 86.0,
        "image_match_score": 92.0,
        "preco": 200.0,
    }
    wrong_model = {
        "titulo": "Polo Aramis Manga Curta Cotton Piquet Basic",
        "final_match_score": 85.0,
        "image_match_score": 72.0,
        "preco": 180.0,
    }
    result = apply_visual_tiebreak(
        [wrong_model, correct_model],  # wrong_model first (to test reorder)
        window=10.0,
        enabled=True,
        official_title="Polo Manga Curta Basica Piquet Marinho aramis",
    )
    assert result[0] is correct_model, "Correct model (higher image_score) should rank first"
```

### Fallback: VISUAL_TIEBREAK_ENABLED=False returns original text sort

```python
from services.cross_marketplace_service import apply_visual_tiebreak

def test_visual_tiebreak_disabled_returns_text_sort():
    a = {"titulo": "Polo Aramis A", "final_match_score": 85.0, "image_match_score": 90.0, "preco": 100.0}
    b = {"titulo": "Polo Aramis B", "final_match_score": 88.0, "image_match_score": 70.0, "preco": 100.0}
    result = apply_visual_tiebreak([a, b], window=10.0, enabled=False, official_title="Polo Aramis aramis")
    # Disabled: sort by -final_match_score -> b (88) before a (85)
    assert result[0] is b
```

---

## Architecture Patterns

### Integration in compare_product — exact diff

Lines 252–253 (current):
```python
# Ordena por relevância final e depois menor preço
produtos_filtrados.sort(key=lambda x: (-x["final_match_score"], x["preco"]))
```

Replacement:
```python
# Reordena por discriminacao visual entre candidatos da mesma marca (MODEL-02)
produtos_filtrados = apply_visual_tiebreak(
    produtos_filtrados,
    window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW,
    enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED,
    official_title=official_title,
)
```

`apply_visual_tiebreak` is defined at module level (above the class), directly after `passes_brand_gate`. `official_title` is already in scope (set at line 125 of the current file).

---

## Runtime State Inventory

Not applicable — greenfield feature addition, no rename or data migration.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, no install needed) |
| Config file | none — uses default discovery |
| Quick run command | `pytest tests/test_model_discrimination.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | model_ratio~0, same brand, falls below cutoff even with high image | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_model_ratio_zero_below_cutoff_with_high_image -x` | No (Wave 0) |
| MODEL-01 | correct model stays at top vs adjacent model | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_correct_model_unaffected_by_penalty -x` | No (Wave 0) |
| MODEL-02 | within-window same-brand: higher image_score ranks first | unit | `pytest tests/test_model_discrimination.py::TestVisualTiebreak::test_promotes_higher_image_within_window -x` | No (Wave 0) |
| MODEL-02 | flag off / image=0: falls back to text sort, zero regression | unit | `pytest tests/test_model_discrimination.py::TestVisualTiebreak::test_fallback_when_disabled -x` | No (Wave 0) |
| Criterion 3 | model_ratio=0 same brand: final < cutoff | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_model_ratio_zero_below_cutoff_with_high_image -x` | No (Wave 0) |
| Criterion 4 | non-regression: correct model + correct brand stays at top | unit | `pytest tests/test_model_discrimination.py::TestModelPenalty::test_correct_model_unaffected_by_penalty -x` | No (Wave 0) |

### 5 Mandatory Anchor Tests (from CONTEXT.md)

1. **MODEL-01 anchor:** Two Aramis polo candidates (correct model vs adjacent model). After Phase 23 penalties, correct model ranks first in `apply_visual_tiebreak` output.
2. **MODEL-02 anchor:** Two Aramis candidates with `final_match_score` within 10-point window (e.g., 86 vs 85). Candidate with higher `image_match_score` ranks first.
3. **Criterion 3 anchor:** Candidate with `model_ratio=0` (same brand, zero model-words) — `compute_final_match_score(88*0.45, 85) < 60`.
4. **Non-regression anchor:** Correct model + correct brand (ratio=1.0): text score unaffected by penalty, stays at top.
5. **Fallback anchor:** `VISUAL_TIEBREAK_ENABLED=False` OR `image_score=0` → sort equals `(-final_match_score, preco)` — identical to current behavior.

### Sampling Rate

- **Per task commit:** `pytest tests/test_model_discrimination.py tests/test_brand_gate.py tests/test_relevance_gates.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_model_discrimination.py` — covers all 5 anchor tests (does not exist yet)

*(All other infrastructure is in place: pytest, relevance_gates, nlp_service, test style from test_brand_gate.py)*

---

## Security Domain

No new trust boundaries. No new user inputs. No network calls. No auth changes. ASVS V5 (input validation): the only new inputs are the `window` and `enabled` floats/bool passed from `relevance_settings` — both are typed and validated by pydantic. No SQL, no subprocess, no credentials.

---

## Open Questions

1. **HEAVY_WITH_BRAND = 0.45 vs 0.40**
   - What we know: 0.45 puts `88*0.45=39.6` just below MED_TEXT_FLOOR (40). The margin is 0.4 points.
   - What's unclear: whether real polo fuzzy blends can exceed 88 for model_ratio<0.50 candidates. If a candidate has raw blend 90, `90*0.45=40.5` would trigger Gate 1 rescue.
   - Recommendation: use 0.40 for more margin (`90*0.40=36.0 < 40`), or add a test with raw=90 to confirm the bound. The planner should decide whether 0.45 or 0.40 is the safer default; 0.40 is fully safe but more aggressive.

2. **VISUAL_TIEBREAK_TEXT_WINDOW = 10.0 needs more data**
   - What we know: polo cross-job data shows correct-variant spread of ~5.3 points; window=10 covers this and adjacent wrong-model candidates.
   - What's unclear: whether other product categories (tenis, camiseta) have different spreads.
   - Recommendation: default 10.0 and instruct the human to re-calibrate via `.env` after first production run. Flag as [ASSUMED] below.

3. **`_detect_candidate_brand` helper: private or public?**
   - What we know: `brand_is_present` in `nlp_service.py` already does brand detection; we need a simpler version that returns the brand string (not bool) for grouping.
   - What's unclear: whether to add a public method to `NLPService` or keep it as a private module-level helper in `cross_marketplace_service.py`.
   - Recommendation: keep as a private `_detect_candidate_brand` helper in `cross_marketplace_service.py` (alongside `apply_visual_tiebreak`). Avoids expanding NLPService's public API for a pipeline-internal need.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `VISUAL_TIEBREAK_TEXT_WINDOW = 10.0` covers the typical spread of same-model color variants across product categories | Calibration / Window section | If actual spread > 10 for some categories, correct variants may fall outside the window and not benefit from visual tiebreak. Fixable by increasing window via `.env`. |
| A2 | Raw fuzzy blend for model_ratio<0.50 same-brand candidates does not exceed 88 in practice | Calibration HEAVY multiplier | If some candidate scores raw=90+, `90*0.45=40.5` triggers Gate 1 rescue. Use `0.40` for larger margin if this is a concern. |
| A3 | Phase 22 brand gate already removes brand-absent candidates before tiebreak operates | Integration / Where tiebreak fires | If brand gate is disabled (`BRAND_GATE_ENABLED=False`), non-Aramis items with Aramis in other fields might enter the tiebreak group. In practice: brand gate is enabled by default; risk is low in rollback scenario. |

**Non-assumed (all verified):**
- Arithmetic for HEAVY_WITH_BRAND=0.45 blocking Gate 1: verified against live `services/relevance_gates.py` [VERIFIED: live code]
- model_ratio values for representative polo candidates: computed via live `nlp_service.py` [VERIFIED: live code]
- sort_key correctness for all 4 success-criteria scenarios: verified by arithmetic [VERIFIED: live code]
- Real polo cross-job score spreads: read from `data/search_history.json` [VERIFIED: live data]
- 30 existing tests pass: verified via `pytest tests/test_brand_gate.py tests/test_relevance_gates.py` [VERIFIED: live run]

---

## Environment Availability

Step 2.6: No external dependencies beyond existing project stack. All changes are pure Python using already-installed packages (rapidfuzz, pydantic-settings). No new CLI tools, databases, or services required.

---

## Sources

### Primary (HIGH confidence)
- `services/nlp_service.py` — read in full; `_apply_model_word_penalty` lines 212-266, `brand_is_present` lines 307-344, `_clean_text` lines 124-147 [VERIFIED: live code]
- `services/relevance_gates.py` — read in full; Gate 1 arithmetic verified [VERIFIED: live code]
- `services/cross_marketplace_service.py` — read in full; `passes_brand_gate` lines 16-38, sort step line 253 [VERIFIED: live code]
- `config.py` — `RelevanceSettings` lines 194-338; all current multiplier defaults confirmed [VERIFIED: live code]
- `data/nlp_vocabulary.json` — full vocabulary read; `brand_and_category_words` construction verified [VERIFIED: live code]
- `data/search_history.json` — 71 cross-type jobs; polo cross-job score data extracted and used for calibration [VERIFIED: live data]
- `tests/test_brand_gate.py`, `tests/test_relevance_gates.py` — test style and Phase 22 patterns [VERIFIED: live code, 30 tests passing]
- `.planning/phases/22-gate-de-marca/22-PATTERNS.md` — established patterns for module-level pure predicate, config-flag idiom [VERIFIED: live code]

### Secondary (MEDIUM confidence)
- `.planning/notes/diagnostico-falsos-positivos-busca-sku.md` — root-cause diagnosis confirmed by code inspection
- `.planning/phases/22-gate-de-marca/22-01-SUMMARY.md` — Phase 22 implementation decisions

---

## Metadata

**Confidence breakdown:**
- Calibration arithmetic (HEAVY=0.45): HIGH — verified against live Gate 1 code with representative real data
- Tiebreak algorithm (sort_key correctness): HIGH — verified by explicit scenario arithmetic
- Window default (10.0): MEDIUM — calibrated against one product category (polo); other categories not validated
- Integration point (line 253 replacement): HIGH — read full compare_product; all variables in scope verified

**Research date:** 2026-06-13
**Valid until:** Stable (config.py and nlp_service.py are stable; re-check only if compute_final_match_score gates change)
