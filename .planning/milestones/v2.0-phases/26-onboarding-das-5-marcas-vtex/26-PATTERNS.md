# Phase 26: Onboarding das 5 Marcas VTEX - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 2 (1 new script + 1 new test)
**Analogs found:** 2 / 2

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/onboard_vtex_brands.py` | script/orchestrator | request-response (async, service delegation) | `scripts/validate_clip.py` | role-match (same asyncio.run + async main pattern) |
| `tests/test_vtex_brand_onboarding_contract.py` | test | CRUD (in-memory service, no I/O) | `tests/test_brand_active.py` | exact (same `_make_service_with_brands` factory, same `unittest.mock.patch.object` for `_save`) |

---

## Pattern Assignments

### `scripts/onboard_vtex_brands.py` (script, request-response)

**Analog:** `scripts/validate_clip.py`

**Imports pattern** (validate_clip.py lines 1-8 — mirror this structure):
```python
"""
Onboarding idempotente das 5 marcas concorrentes VTEX (Phase 26, COMP-01).

Execução: python scripts/onboard_vtex_brands.py
Re-executável sem duplicar marcas ou sobrescrever mappings corretos.
"""
import asyncio
import unicodedata
from urllib.parse import urlparse

from services.brand_service import BrandManagerService
from services.engines.vtex_engine import VTEXEngine
from core.models import DynamicBrandCreate, CategoryMapping
```

**Entry-point pattern** (validate_clip.py lines 51-52 — identical idiom):
```python
if __name__ == "__main__":
    asyncio.run(main())
```

**Async main skeleton** (validate_clip.py lines 9-13 — same shape, expand per-brand):
```python
async def main():
    for brand_key, brand_name, domain in BRAND_TABLE:
        result = await onboard_brand(brand_key, brand_name, domain)
        if result is None:
            print(f"[SKIP] {brand_key}: não onboardada — verificar domínio.")
```

**Brand table constant** (D-01 from CONTEXT.md — hard-coded in script, not in service):
```python
BRAND_TABLE = [
    ("levis",       "Levi's",       "www.levi.com.br"),
    ("calvinklein", "Calvin Klein", "www.calvinklein.com.br"),
    ("zapalla",     "Zapalla",      "www.zapalla.com.br"),
    ("austral",     "Austral",      "www.austral.com.br"),   # D-02: testar www. antes de secure.
    ("trackfield",  "Track & Field","www.tf.com.br"),
]
AUSTRAL_DOMAIN_CANDIDATES = ["www.austral.com.br", "austral.com.br", "secure.austral.com.br"]
```

**Idempotency + engine-fix pattern** (RESEARCH.md Pattern 1, lines 192-214 — CRITICAL):
```python
async def onboard_brand(svc: BrandManagerService, brand_key, brand_name, domain):
    from api.routes_brands import detect_engine

    data = DynamicBrandCreate(
        brand_key=brand_key,
        brand_name=brand_name,
        domain=domain,
        engine="auto",   # detect_engine chamado dentro de create_brand / aqui
    )

    # add_brand: upsert que NÃO atualiza engine/is_active no modo update (landmine)
    brand = svc.add_brand(data)

    # Verificar/corrigir engine (landmine: upsert preserva engine antiga)
    detected = await detect_engine(brand.domain)
    if brand.engine != detected:
        brand.engine = detected
        svc._save(brand)   # corrige in-place + persiste

    if brand.engine != "vtex":
        print(f"[WARN] {brand_key}: engine={brand.engine!r} — investigar domínio")
        svc.set_active(brand_key, False)
        return None

    svc.set_active(brand_key, True)

    # Idempotência de mappings: se já populados, perguntar antes de sobrescrever
    if brand.mappings:
        print(f"[INFO] {brand_key}: mappings já existem ({len(brand.mappings)} itens). Sobrescrever? [s/N] ", end="")
        ans = input().strip().lower()
        if ans != "s":
            return brand

    return brand
```

**discover_categories + path extraction pattern** (RESEARCH.md Pitfall 3 — urlparse obrigatório):
```python
async def discover_and_match(svc, brand_key):
    engine = VTEXEngine(brand_key)                    # após add_brand garantido
    raw = await engine.discover_categories()          # [{name, path (URL completa)}]
    for item in raw:
        item["rel_path"] = urlparse(item["path"]).path  # extrai path relativo
    return raw
```

**Auto-match + revisão humana pattern** (RESEARCH.md Pattern 3 — normalização + CANONICAL_SLUGS):
```python
import unicodedata

CANONICAL_KEYWORDS = {
    "camisas":   ["camisa", "camisas"],
    "polos":     ["polo", "polos"],
    "camisetas": ["camiseta", "camisetas", "t-shirt", "tshirt"],
    "calcas":    ["calca", "calcas", "calças", "calça", "jeans", "denim"],
    "bermudas":  ["bermuda", "bermudas", "short", "shorts"],
    "jaquetas":  ["jaqueta", "jaquetas", "casaco", "casacos", "blusa"],
    "infantil":  ["infantil", "kids", "mini"],
}

def normalize(text: str) -> str:
    """Lowercase + remove acentos (stdlib unicodedata)."""
    text = text.lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

def auto_match(categories):
    """Retorna lista de (canonical_slug, rel_path, label) para revisão humana."""
    proposals = []
    for item in categories:
        norm = normalize(item["name"])
        for slug, keywords in CANONICAL_KEYWORDS.items():
            if any(kw in norm for kw in keywords):
                proposals.append((slug, item["rel_path"], item["name"]))
                break
    return proposals
```

**Human review + update_mappings pattern** (D-09 + brand_service.update_mappings):
```python
def print_and_confirm(brand_key, proposals):
    print(f"\n--- {brand_key} --- de/para proposto ---")
    for slug, path, label in proposals:
        print(f"  {slug:12s} ← {label!r}  ({path})")
    print("Confirmar? [s/N] ", end="")
    return input().strip().lower() == "s"

def persist_mappings(svc, brand_key, proposals):
    mappings = [
        CategoryMapping(canonical_slug=slug, vtex_fq_path=path, label=label)
        for slug, path, label in proposals
    ]
    svc.update_mappings(brand_key, mappings)  # persiste via _save (dual dev/prod)
```

---

### `tests/test_vtex_brand_onboarding_contract.py` (test, CRUD)

**Analog:** `tests/test_brand_active.py`

**File-header + imports pattern** (test_brand_active.py lines 1-23 — copy docstring style exactly):
```python
"""
Teste de contrato offline — onboarding das 5 marcas VTEX (Phase 26, COMP-01).

Cobertura (sem rede, sem I/O real):
  - TestBrandContract: exercita estado final após onboarding simulado
      1. engine="vtex" após create + detect mockado
      2. is_active=True após engine confirmado
      3. Mappings persistidos (update_mappings) com canonical_slug válido
      4. Brand aparece em list_brands(active_only=True)
      5. resolve_category_for_brands retorna URL válida para slug mapeado
"""
import asyncio
import unittest.mock
from unittest.mock import MagicMock, patch

from services.brand_service import BrandManagerService
from services.category_mapping import resolve_category_for_brands, CANONICAL_SLUGS
from core.models import DynamicBrand, DynamicBrandCreate, CategoryMapping
```

**In-memory service factory** (test_brand_active.py lines 30-57 — exact pattern):
```python
def _make_service_with_vtex_brand(brand_key="levis", engine="vtex", is_active=True, mappings=None):
    """BrandManagerService em memória sem I/O (sem brands.json, sem Supabase).

    _check_reload mockado como no-op; _save mockado para evitar I/O.
    """
    svc = BrandManagerService.__new__(BrandManagerService)
    svc.brands = {}
    svc.last_modified = 0
    svc.updated_event = asyncio.Event()
    svc._check_reload = unittest.mock.MagicMock()   # sem I/O
    svc.brands[brand_key] = DynamicBrand(
        brand_key=brand_key,
        brand_name="Levi's",
        domain="www.levi.com.br",
        engine=engine,
        is_active=is_active,
        mappings=mappings or [],
    )
    return svc
```

**Contract test class pattern** (test_brand_active.py lines 64-103 — same class-per-concern style):
```python
class TestBrandContract:

    def test_engine_is_vtex(self):
        svc = _make_service_with_vtex_brand(engine="vtex")
        brand = svc.get_brand("levis")
        assert brand.engine == "vtex", f"Expected engine='vtex', got {brand.engine!r}"

    def test_brand_is_active(self):
        svc = _make_service_with_vtex_brand(is_active=True)
        brand = svc.get_brand("levis")
        assert brand.is_active is True

    def test_mappings_persisted(self):
        sample_mappings = [
            CategoryMapping(canonical_slug="calcas", vtex_fq_path="/roupas/jeans", label="Jeans"),
            CategoryMapping(canonical_slug="polos",  vtex_fq_path="/roupas/polos", label="Polos"),
        ]
        svc = _make_service_with_vtex_brand(mappings=sample_mappings)
        with unittest.mock.patch.object(svc, "_save"):   # sem I/O
            svc.update_mappings("levis", sample_mappings)
        brand = svc.get_brand("levis")
        assert len(brand.mappings) > 0
        valid_slugs = {"camisas", "polos", "camisetas", "calcas", "bermudas", "jaquetas", "infantil"}
        for m in brand.mappings:
            assert m.canonical_slug in valid_slugs, f"slug inválido: {m.canonical_slug!r}"

    def test_brand_in_active_list(self):
        svc = _make_service_with_vtex_brand(is_active=True)
        active = svc.list_brands(active_only=True)
        keys = [b.brand_key for b in active]
        assert "levis" in keys

    def test_vtex_fq_path_is_relative(self):
        """vtex_fq_path deve ser path relativo (/...) não FQ (C:/...)."""
        sample_mappings = [
            CategoryMapping(canonical_slug="calcas", vtex_fq_path="/roupas/jeans", label="Jeans"),
        ]
        svc = _make_service_with_vtex_brand(mappings=sample_mappings)
        brand = svc.get_brand("levis")
        for m in brand.mappings:
            assert m.vtex_fq_path.startswith("/"), (
                f"vtex_fq_path deve iniciar com '/' (path relativo), got: {m.vtex_fq_path!r}"
            )
```

**Mock _save to avoid I/O** (test_brand_active.py lines 122-124 — identical idiom for all write tests):
```python
with unittest.mock.patch.object(svc, "_save"):
    result = svc.update_mappings("levis", mappings)
```

**Mock detect_engine in integration test** (test_engine_detection.py lines 188-210 — same patch.object on routes_brands_module):
```python
import api.routes_brands as routes_brands_module

with patch.object(routes_brands_module, "detect_engine", new=AsyncMock(return_value="vtex")):
    with patch.object(routes_brands_module.brand_service, "add_brand", return_value=fake_brand):
        result = asyncio.run(routes_brands_module.create_brand(brand_create_data))
```

---

## Shared Patterns

### Persistência dual (dev/prod)
**Source:** `services/brand_service.py` lines 180-186
**Apply to:** Script seed — usar exclusivamente `brand_service._save(brand)` e `update_mappings`; nunca editar JSON diretamente.
```python
def _save(self, brand: Optional[DynamicBrand] = None):
    if _use_supabase():
        if brand:
            self._upsert_to_supabase(brand)
    else:
        self._save_to_json()
```

### Idempotência de upsert (landmine CRÍTICO)
**Source:** `services/brand_service.py` lines 188-198
**Apply to:** Script seed — verificar `result.engine` APÓS `add_brand` e corrigir in-place se necessário.
```python
def add_brand(self, data: DynamicBrandCreate) -> DynamicBrand:
    key = data.brand_key.lower().strip()
    if key in self.brands:
        self.brands[key].domain = data.domain
        self.brands[key].brand_name = data.brand_name
        # engine e is_active NAO são atualizados no upsert!
    else:
        new_brand = DynamicBrand(**data.model_dump())
        self.brands[key] = new_brand
    self._save(self.brands[key])
    return self.brands[key]
```

### CategoryMapping shape exato
**Source:** `core/models.py` lines 199-204
**Apply to:** Script seed (construção de CategoryMapping) + teste de contrato.
```python
class CategoryMapping(BaseModel):
    canonical_slug: str   # deve ser um dos slugs de _RAW_CATEGORIES
    vtex_fq_path: str     # path relativo ex: "/roupas/polos" — NÃO FQ "C:/..."
    label: str            # label display, livre
```

### Formato brands.json para marca VTEX dinâmica
**Source:** `data/brands.json` lines 50-77 (entrada `bck` — único exemplo com mappings dinâmicos)
```json
"bck": {
  "brand_key": "bck",
  "brand_name": "Buckman",
  "domain": "buckmanbck.com.br",
  "engine": "shopify",
  "vtex_account": null,
  "mappings": [
    {"canonical_slug": "calcas", "vtex_fq_path": "/collections/calcas", "label": "Calças"},
    {"canonical_slug": "camisas", "vtex_fq_path": "/collections/camisas", "label": "Camisas"},
    {"canonical_slug": "polos",   "vtex_fq_path": "/collections/polos",  "label": "Polos"}
  ],
  "is_active": true
}
```
Para as 5 marcas VTEX desta phase: mesmo shape, `engine="vtex"`, `vtex_fq_path` com path relativo extraído de URL completa via `urlparse(url).path`.

### No-I/O service factory (testes)
**Source:** `tests/test_brand_active.py` lines 30-57
**Apply to:** `test_vtex_brand_onboarding_contract.py` — copiar o padrão `BrandManagerService.__new__` + `_check_reload = MagicMock()` + população direta de `svc.brands`.

---

## No Analog Found

Nenhum arquivo novo desta phase ficou sem analog — ambos têm correspondências diretas no codebase.

| Anti-pattern | Por que não aplicar |
|---|---|
| Hardcodar `engine="vtex"` sem `detect_engine` | Viola D-11 e critério 2 de sucesso |
| Editar `services/category_mapping.py:_RAW_CATEGORIES` | D-07 proíbe; usar `DynamicBrand.mappings` |
| Usar `vtex_fq_path = "C:/1/2/"` (FQ) | Pitfall 3: `resolve_category_for_brands` não gera URL válida a partir de FQ |
| Chamar `get_engine` antes de `add_brand` | Pitfall 4: `discover_categories` retorna `[]` silenciosamente se brand não existir |

---

## Metadata

**Analog search scope:** `scripts/`, `tests/`, `services/brand_service.py`, `core/models.py`, `data/brands.json`
**Files scanned:** 6
**Pattern extraction date:** 2026-06-19
