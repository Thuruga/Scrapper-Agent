# Phase 23: Discriminação de Modelo - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 4 (2 modified services, 1 modified config, 1 new test)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `config.py` | config | n/a | `config.py` lines 215-224 (`BRAND_GATE_ENABLED`) and lines 265-276 (`NLP_MODEL_PENALTY_*`) | exact |
| `services/cross_marketplace_service.py` | service / pipeline | request-response (list reorder) | `passes_brand_gate` (same file, lines 16-38) — module-level pure function | exact |
| `services/nlp_service.py` | service / domain | transform (read-only consumer) | `_apply_model_word_penalty` (same file, lines 212-266) — multiplier consumer | exact (no structural change) |
| `tests/test_model_discrimination.py` | test | n/a | `tests/test_brand_gate.py` (entire file) | role-match (Phase 22 house style) |

## Purity Boundary (LOCKED)

`services/relevance_gates.py` — NO CHANGES. This module is pure (no network, no AI, no state). Cross-candidate and brand-aware logic lives in `cross_marketplace_service.py`, not here. This constraint mirrors Phase 22 and is an explicit architectural lock. The planner must flag any plan action that touches `relevance_gates.py` as out-of-scope.

---

## Pattern Assignments

### `config.py` (config)

**Analog:** `config.py` lines 215-224 (`BRAND_GATE_ENABLED`) for the new bool flag; lines 265-276 (`NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` / `NLP_MODEL_PENALTY_MED_WITH_BRAND`) for the two adjusted defaults.

**Bool flag idiom** (lines 215-224 — copy this structure for `VISUAL_TIEBREAK_ENABLED`):
```python
# ---- Gate de marca (BRAND-02 / BRAND-03) --------------------------------
BRAND_GATE_ENABLED: bool = Field(
    default=True,
    description=(
        "Quando True, descarta itens cujo título não contém nenhuma das "
        "marcas conhecidas presentes na query. No-op se a query não "
        "especifica marca conhecida. Configurável via .env "
        "(BRAND_GATE_ENABLED=false para desativar)."
    ),
)
```

**Float Field idiom with description** (lines 265-276 — current values to be changed):
```python
NLP_MODEL_PENALTY_HEAVY_WITH_BRAND: float = Field(
    default=0.70,   # <- CHANGE TO 0.45 (see calibration arithmetic in RESEARCH.md)
    description="Multiplicador de penalidade pesada quando marca está presente (suaviza).",
)
NLP_MODEL_PENALTY_MED_WITH_BRAND: float = Field(
    default=0.90,   # <- CHANGE TO 0.75
    description="Multiplicador de penalidade moderada quando marca está presente.",
)
```

**New fields to add after the `BRAND_GATE_ENABLED` block** (lines 224-225 is the natural insertion point — before the NLP weight block):
```python
# ---- Discriminação de modelo visual (MODEL-02) --------------------------
VISUAL_TIEBREAK_ENABLED: bool = Field(
    default=True,
    description=(
        "Quando True, candidatos da mesma marca com scores de texto dentro "
        "de VISUAL_TIEBREAK_TEXT_WINDOW são reordenados pelo score visual "
        "(CLIP). Rollback: VISUAL_TIEBREAK_ENABLED=false desativa sem "
        "alterar código."
    ),
)
VISUAL_TIEBREAK_TEXT_WINDOW: float = Field(
    default=10.0,
    description=(
        "Janela de ambiguidade de texto (pontos 0-100): candidatos da mesma "
        "marca dentro desta faixa do top-score da marca são reordenados pelo "
        "score visual. Default 10.0 cobre a dispersão típica de variantes de "
        "cor (~5.3 pontos) mais candidatos de modelo adjacente (~8 pontos)."
    ),
)
```

---

### `services/cross_marketplace_service.py` (service, request-response)

**Analog:** `passes_brand_gate` (lines 16-38) — the exact module-level pure function pattern to mirror for `apply_visual_tiebreak`.

**Module-level pure function pattern to copy** (lines 16-38):
```python
def passes_brand_gate(titulo: str, official_title: str, enabled: bool) -> bool:
    """
    Predicado puro de nível de módulo para o gate de marca.
    ...
    Args:
        titulo: Título bruto (raw) do produto do marketplace.
        official_title: Título oficial bruto da query (produto buscado).
        enabled: Flag BRAND_GATE_ENABLED lida de relevance_settings pelo chamador.

    Returns:
        bool — True para manter o item, False para descartá-lo.
    """
    return (not enabled) or nlp_service.brand_is_present(official_title, titulo)
```

**Key idioms to preserve in `apply_visual_tiebreak`:**
- Defined at module level (before the class), directly after `passes_brand_gate`
- Receives `window` and `enabled` as arguments — never reads `relevance_settings` internally (anti-tautology HIGH-1, mirrors `passes_brand_gate(enabled=...)`)
- Returns a new list (`sorted(...)`) — does NOT mutate in-place (unlike the current line 253 `.sort()`)
- Falls back to `sorted(candidates, key=lambda x: (-x["final_match_score"], x["preco"]))` when disabled or no image signal — zero regression
- Private helper `_detect_candidate_brand(titulo, vocab_brands)` defined at module level alongside it

**Calling site — current sort at line 253 (to be replaced):**
```python
# BEFORE (line 253):
produtos_filtrados.sort(key=lambda x: (-x["final_match_score"], x["preco"]))

# AFTER (reassignment — apply_visual_tiebreak returns a new list):
produtos_filtrados = apply_visual_tiebreak(
    produtos_filtrados,
    window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW,
    enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED,
    official_title=official_title,
)
```

`official_title` is already in scope at line 253 (set earlier in `compare_product`). `relevance_settings` is already imported at line 6.

**Existing imports** (lines 1-8 — no new imports needed):
```python
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Any, Optional

from config import relevance_settings
from services import relevance_gates
from services.nlp_service import nlp_service
```

`nlp_service._vocab.known_brands_for_detection` and `nlp_service._clean_text` are accessed via the already-imported `nlp_service` singleton — no new imports.

---

### `services/nlp_service.py` (service, transform — READ-ONLY CONFIRMATION)

**No structural changes.** This file is included in the map only to confirm the consumer of the adjusted config values and the helpers available for reuse.

**Multiplier consumer** (`_apply_model_word_penalty`, lines 212-266): reads `relevance_settings.NLP_MODEL_PENALTY_HEAVY_WITH_BRAND` and `NLP_MODEL_PENALTY_MED_WITH_BRAND` from the config singleton. Changing the defaults in `config.py` is sufficient — zero code change in this file for MODEL-01.

**Helpers available for `_detect_candidate_brand` in `cross_marketplace_service.py`:**
- `nlp_service._clean_text(text)` — full normalization pipeline (unescape, strip, NFD, lowercase, noise words)
- `nlp_service._vocab.known_brands_for_detection` — frozenset `{"aramis", "reserva", "tommy"}` (single source of truth)
- `nlp_service.brand_is_present(official_title, titulo)` — already used by `passes_brand_gate`

---

### `tests/test_model_discrimination.py` (test — NEW FILE)

**Analog:** `tests/test_brand_gate.py` (entire file) — Phase 22 house style.

**Module docstring pattern** (lines 1-19 of test_brand_gate.py):
```python
"""
Testes do gate de marca (Phase 22 — BRAND-01, BRAND-02, BRAND-03).

Cobertura:
  - TestBrandGate: exercita NLPService.brand_is_present diretamente
      ...
  - TestBrandGatePredicate: exercita o MESMO objeto de código usado em produção
      ...
"""
```

**Import idiom** (lines 20-22):
```python
from services import relevance_gates
from services.cross_marketplace_service import passes_brand_gate
from services.nlp_service import nlp_service
```

For Phase 23 mirror:
```python
from services import relevance_gates
from services.cross_marketplace_service import apply_visual_tiebreak
from services.nlp_service import nlp_service
```

**Class + test method style** (lines 37-58):
```python
class TestBrandGate:
    def test_hering_polo_discarded_against_aramis_query(self):
        # Caso-âncora: query oficial Aramis vs título Hering — marca ausente → descartado
        assert nlp_service.brand_is_present(
            _OFFICIAL_ARAMIS,
            _TITLE_HERING,
        ) is False
```

**Style rules to preserve:**
- One `class Test<Behavior>:` per behavior cluster (e.g. `TestModelPenalty`, `TestVisualTiebreak`)
- Plain `def test_...` methods, no pytest fixtures unless genuinely needed
- `assert ... is True` / `assert ... is False` for booleans (not `== True`)
- `assert ... < 60.0` with f-string message for float comparisons: `assert final < 60.0, f"Wrong-model item should be below cutoff, got {final}"`
- Module-level constants for repeated fixture data (e.g. `_OFFICIAL_ARAMIS`)
- Inline comment on each test explaining the gate condition being verified

**5 mandatory anchor tests** (class structure):

```python
class TestModelPenalty:
    # Anchor 3 / criterion 3: model_ratio=0, same brand, falls BELOW cutoff even with high image
    def test_model_ratio_zero_below_cutoff_with_high_image(self): ...

    # Anchor 4 / criterion 4: correct model (ratio >= 0.75) unaffected by penalty
    def test_correct_model_unaffected_by_penalty(self): ...

class TestVisualTiebreak:
    # Anchor 1 (MODEL-01): correct model ranks above adjacent model after Phase 23 penalties
    def test_correct_model_ranks_above_adjacent(self): ...

    # Anchor 2 (MODEL-02): within-window same-brand → higher image_score ranks first
    def test_promotes_higher_image_within_window(self): ...

    # Anchor 5: flag off / image=0 → fallback to text sort, zero regression
    def test_fallback_when_disabled(self): ...
```

---

## Shared Patterns

### Module-level pure function (anti-tautology HIGH-1)
**Source:** `services/cross_marketplace_service.py` lines 16-38 (`passes_brand_gate`)
**Apply to:** `apply_visual_tiebreak` and `_detect_candidate_brand` in the same file
- Defined at module scope (not as class methods)
- All state passed as arguments — no internal reads of `relevance_settings`
- Importable directly by tests: `from services.cross_marketplace_service import apply_visual_tiebreak`

### Config-flag read inline by caller, passed as argument to pure function
**Source:** `services/cross_marketplace_service.py` line 249 (`passes_brand_gate(..., relevance_settings.BRAND_GATE_ENABLED)`)
**Apply to:** caller of `apply_visual_tiebreak` at line 253 replacement
```python
# Caller reads the flag; function receives it as a plain bool
produtos_filtrados = apply_visual_tiebreak(
    produtos_filtrados,
    window=relevance_settings.VISUAL_TIEBREAK_TEXT_WINDOW,
    enabled=relevance_settings.VISUAL_TIEBREAK_ENABLED,
    official_title=official_title,
)
```

### Field(default=..., description=...) idiom
**Source:** `config.py` lines 215-276 (all `RelevanceSettings` fields)
**Apply to:** `VISUAL_TIEBREAK_ENABLED` and `VISUAL_TIEBREAK_TEXT_WINDOW` additions; `.env`-overridable by construction (pydantic-settings), no extra wiring needed.

### Vocabulary single source of truth
**Source:** `nlp_service._vocab.known_brands_for_detection` (frozenset backed by `data/nlp_vocabulary.json` key `known_brands_for_brand_detection`)
**Apply to:** `_detect_candidate_brand` helper — must use this frozenset, never a literal brand list.

### Purity boundary (LOCKED Phase 22)
**Source:** `services/relevance_gates.py` module (unchanged since Phase 22)
**Apply to:** all Phase 23 changes — cross-candidate logic and brand knowledge stay in `cross_marketplace_service.py`. No title/brand arguments added to `relevance_gates` functions.

---

## No Analog Found

None. Every new/modified file has a strong in-codebase analog.

---

## Metadata

**Analog search scope:** `services/cross_marketplace_service.py`, `config.py`, `services/nlp_service.py`, `tests/test_brand_gate.py`, `.planning/phases/22-gate-de-marca/22-PATTERNS.md`
**Files scanned (live reads):** 6
**Pattern extraction date:** 2026-06-13
