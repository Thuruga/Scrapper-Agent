# Phase 22: Gate de Marca - Pattern Map

**Mapped:** 2026-06-13
**Files analyzed:** 4 (1 modified service, 1 modified service, 1 modified config, 1 new test)
**Analogs found:** 4 / 4 (all in-codebase, exact/role matches)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `services/nlp_service.py` (new public method `brand_is_present`) | service / domain helper | transform (pure string → bool) | `NLPService._apply_brand_penalty` (same file, lines 307-328) | exact (same trigger, same vocab, same normalization) |
| `services/cross_marketplace_service.py` (new post-score filter step) | service / pipeline | request-response (list filter) | `produtos_filtrados` list-comprehension (same file, lines 218-223) | exact (same insertion point, same dict shape) |
| `config.py` (new `BRAND_GATE_ENABLED` flag in `RelevanceSettings`) | config | n/a | `CROSS_MIN_SCORE_WITH_VISION` / `PLAYWRIGHT_AMAZON_FALLBACK` Field entries (lines 198-201, 314-320) | exact (bool flag idiom + non-flag Field idiom) |
| `tests/test_brand_gate.py` (new unit tests) | test | n/a | `tests/test_relevance_gates.py` (whole file) | role-match (no NLP test file exists yet; gates test is the canonical style) |

## Pattern Assignments

### `services/nlp_service.py` — new public method `brand_is_present` (service, transform)

**Analog:** `NLPService._apply_brand_penalty` in the same file (lines 307-328). This method already implements the exact trigger and discard logic the gate needs; the new public helper is a boolean refactor of it.

**Trigger + intersection + match pattern to mirror** (lines 307-328):
```python
def _apply_brand_penalty(self, score: float, clean_official: str, clean_market: str) -> float:
    official_words = set(clean_official.split())
    market_words = set(clean_market.split())

    # Quais marcas estão presentes na query original?
    brands_in_query = official_words.intersection(self._vocab.known_brands_for_detection)

    if not brands_in_query:
        return score # A query não especifica marca, não penaliza.

    # Pelo menos uma das marcas da query deve estar no título do marketplace
    if any(b in market_words for b in brands_in_query):
        return score # Marca encontrada!

    return score * 0.50
```

**Normalization to reuse — do NOT reimplement** (`_clean_text`, lines 124-147): unescape HTML → strip `®™|-` → NFD ASCII → `utils.default_process` (lowercase + squash whitespace) → remove `noise_words`. The brand gate MUST run candidate titles through this same `_clean_text` before tokenizing, exactly like `calculate_text_score` does at lines 179-180.

**Vocabulary accessor to reuse** (`NLPVocabulary.known_brands_for_detection`, lines 84-86):
```python
@cached_property
def known_brands_for_detection(self) -> FrozenSet[str]:
    return frozenset(self._data.get("known_brands_for_brand_detection", []))
```
Today this resolves to `["aramis", "reserva", "tommy"]` (see `data/nlp_vocabulary.json` lines 71-75).

**Recommended new method shape** (returns bool, no score — keeps the gate decision in the service):
```python
def brand_is_present(self, official_title: str, marketplace_title: str) -> bool:
    """
    True se a query NÃO especifica marca conhecida (no-op → mantém item)
    OU se o título do marketplace contém ao menos uma das marcas da query.
    False apenas quando a query especifica marca conhecida e o título do
    marketplace não a contém (item a descartar).
    """
    clean_official = self._clean_text(official_title)
    clean_market = self._clean_text(marketplace_title)
    official_words = set(clean_official.split())
    market_words = set(clean_market.split())

    brands_in_query = official_words.intersection(self._vocab.known_brands_for_detection)
    if not brands_in_query:
        return True  # no-op: query sem marca conhecida não filtra nada
    return any(b in market_words for b in brands_in_query)
```
Note: pass RAW titles and clean inside (matches `calculate_text_score` ownership of cleaning), OR accept pre-cleaned strings to mirror `_apply_brand_penalty`'s signature. Planner picks one; prefer raw-in/clean-inside so the service caller stays vocabulary-agnostic.

---

### `services/cross_marketplace_service.py` — new post-score brand filter (service, request-response)

**Analog:** the existing `produtos_filtrados` comprehension (lines 218-223) and its surrounding flow.

**Exact insertion point** — AFTER `final_match_score` is computed for every product (text-only at line 133, or combined via `compute_final_match_score` at lines 194-204) and BEFORE / merged-into the cutoff comprehension. The existing cutoff (lines 214-223):
```python
actual_min_score = relevance_gates.compute_min_score_cutoff(
    min_score, ref_embed is not None
)
produtos_filtrados = [
    p
    for p in todos_produtos
    if p.get("final_match_score", 0) >= actual_min_score
    and p.get("preco", 0) > 0
]
```

**Pattern to copy** — add the brand gate as an independent predicate alongside the existing score/price predicates. `official_title` is already in scope in this method (used at line 128). `relevance_gates.py` stays pure (do NOT pass brand/title to it):
```python
from services.nlp_service import nlp_service  # já importado no escopo (linha 124)

produtos_filtrados = [
    p
    for p in todos_produtos
    if p.get("final_match_score", 0) >= actual_min_score
    and p.get("preco", 0) > 0
    and (
        not relevance_settings.BRAND_GATE_ENABLED
        or nlp_service.brand_is_present(official_title, p.get("titulo", ""))
    )
]
```
Config-flag read mirrors how `relevance_settings.*` is already consumed inline throughout this method (e.g. line 133 `relevance_settings.FINAL_TEXT_WEIGHT`, line 237 `relevance_settings.CROSS_MAX_RESULTS_PER_PLATFORM_FINAL`). No hardcode in the decision flow.

**Product dict access pattern** to copy: candidates are dicts; title is `p.get("titulo", "")` (line 128), score is `p.get("final_match_score", 0)` (line 221). The brand gate operates on `todos_produtos` before the per-platform cap (lines 234-240) and before dedup (line 305) — so absent-brand look-alikes never reach PDP fetch or buybox selection.

---

### `config.py` — new `BRAND_GATE_ENABLED` flag in `RelevanceSettings` (config)

**Analog (bool flag idiom):** `PLAYWRIGHT_AMAZON_FALLBACK` (lines 314-320) and the simpler bool fields like `ENABLE_PROXY` (line 63).

**Analog (Field default + description idiom used across the whole class):** `CROSS_MIN_SCORE_WITH_VISION` (lines 198-201):
```python
CROSS_MIN_SCORE_WITH_VISION: float = Field(
    default=60.0,
    description="Score mínimo (0-100) quando a IA visual (CLIP) está ativa.",
)
```

**Pattern to copy** — add to `RelevanceSettings` (after the cutoff thresholds block, lines 197-213, is a natural home since this is a cutoff-related gate). Default ACTIVE per CONTEXT (BRAND-03):
```python
# ---- Gate de marca (BRAND-02 / BRAND-03) --------------------------------
BRAND_GATE_ENABLED: bool = Field(
    default=True,
    description=(
        "Quando True, descarta itens cujo título não contém nenhuma das "
        "marcas conhecidas presentes na query. No-op se a query não "
        "especifica marca conhecida."
    ),
)
```
`RelevanceSettings` already loads from `.env` with `extra="ignore"` (lines 322-327), so the flag is overridable via `BRAND_GATE_ENABLED=false` with zero extra wiring. Consumed via the singleton `relevance_settings` (line 332).

---

### `tests/test_brand_gate.py` — new unit tests (test)

**Analog:** `tests/test_relevance_gates.py` (entire file). No NLP-specific test file exists (`tests/test_*nlp*.py` → none found), so this gates test defines the house style.

**Style to copy:**
- Module docstring describing what is covered (lines 1-6).
- `from services import X` import idiom (line 11): `from services.nlp_service import nlp_service` or import `NLPService`/`NLPVocabulary` for an isolated instance with a controlled vocab.
- One `class Test<Behavior>:` per behavior cluster, plain `def test_...` methods (e.g. `TestFinalMatchScore`, lines 17-60).
- Plain `assert` with inline comment explaining the gate condition (lines 18-25).
- `pytest.approx(...)` for float comparisons (lines 42, 46) — N/A here since `brand_is_present` returns bool; use `is True` / `is False` like `TestBuyboxWinner` (lines 172-173).
- Small private fixture-builder helpers on the class when inputs are structured (e.g. `_make_result`, lines 85-95; `_r`, line 127). For this phase a helper returning the official title is optional since inputs are plain strings.

**Mandatory anchor test (from CONTEXT specifics, lines 92-98):**
```python
class TestBrandGate:
    def test_hering_polo_discarded_against_aramis_query(self):
        # query oficial Aramis vs título Hering -> marca ausente -> descartado
        assert nlp_service.brand_is_present(
            "Camisa Polo Aramis Masculina aramis",
            "Camisa Polo Básica Masculina Manga Curta Em Piquet Hering",
        ) is False

    def test_aramis_title_passes(self):  # não-regressão: 95% dos casos reais
        assert nlp_service.brand_is_present(
            "Camisa Polo Aramis aramis",
            "Camisa Polo Aramis Masculina Piquet",
        ) is True

    def test_noop_when_query_has_no_known_brand(self):  # gate não filtra
        assert nlp_service.brand_is_present(
            "Camisa Polo Masculina Piquet",
            "Camisa Polo Hering",
        ) is True
```
Also recommended: a `cross_marketplace_service` integration-style test asserting the Hering item is dropped from `produtos_filtrados` even when `compute_final_match_score(40.9, 85) == 85` (the documented leak). Verify the no-op path keeps items when `BRAND_GATE_ENABLED=False`.

## Shared Patterns

### Vocabulary-driven brand trigger
**Source:** `services/nlp_service.py` `NLPVocabulary.known_brands_for_detection` (lines 84-86) backed by `data/nlp_vocabulary.json` key `known_brands_for_brand_detection` (lines 71-75).
**Apply to:** the new `brand_is_present` helper. Single source of truth — the gate trigger must read from this frozenset, never a literal list. Mirrors `_apply_brand_penalty` (line 317) and `_apply_model_word_penalty` (line 248).

### Text normalization before token comparison
**Source:** `services/nlp_service.py` `_clean_text` (lines 124-147).
**Apply to:** the brand gate, both sides (official + marketplace title), exactly as `calculate_text_score` does at lines 179-180. Guarantees accent/case/noise-word parity with the existing penalty path so the gate and the penalty agree on what "contains the brand" means.

### Config-flag read inline, no hardcode
**Source:** `services/cross_marketplace_service.py` inline `relevance_settings.*` reads (lines 133, 215, 237) + `config.py` `RelevanceSettings` Field idiom (lines 198-213).
**Apply to:** `BRAND_GATE_ENABLED` and any future threshold. Decision flow reads the flag at the comprehension; default-on, `.env`-overridable.

### Purity boundary
**Source:** `services/relevance_gates.py` module docstring (lines 1-11) — "sem rede, sem IA, sem estado".
**Apply to:** keep `relevance_gates.py` untouched. The brand gate lives entirely in `nlp_service` (helper) + `cross_marketplace_service` (filter step). No brand/title arguments leak into the pure gate functions. (LOCKED decision, CONTEXT lines 38-39.)

## No Analog Found

None. Every new/modified file has a strong in-codebase analog; RESEARCH.md fallback patterns are not needed for this phase.

## Metadata

**Analog search scope:** `services/`, `config.py`, `data/nlp_vocabulary.json`, `tests/`
**Files scanned:** 7 (CONTEXT, relevance_gates, config, test_relevance_gates, nlp_service, nlp_vocabulary, cross_marketplace_service) + glob for NLP tests
**Pattern extraction date:** 2026-06-13
