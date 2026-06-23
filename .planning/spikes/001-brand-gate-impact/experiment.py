"""
Spike 001: Impacto do gate rígido de marca sobre dados reais.

Mede, nos 71 jobs `cross` reais de data/search_history.json, o que aconteceria se a
penalidade suave de marca (score * 0.50 em nlp_service._apply_brand_penalty) fosse trocada
por um GATE RÍGIDO: descartar todo item cujo título do marketplace NÃO contenha a marca
especificada na query.

Limitação dos dados: o histórico só guarda os itens que PASSARAM a régua (os exibidos).
Logo medimos o impacto do gate sobre os itens hoje exibidos — que é exatamente a pergunta:
"o gate rígido derrubaria itens que hoje aparecem, e quais deles eram legítimos?"

Classificação de cada item que o gate derrubaria (título sem a marca da query), usando o
image_match_score CLIP já armazenado como proxy de verdade-terrena:
  - PERDA DE COBERTURA (legítimo): img >= VIS_LEGIT  -> é o produto certo, só omitiu a marca
  - GANHO DE PRECISÃO (ruído):     img <  VIS_NOISE  -> provável marca/modelo errado
  - AMBÍGUO:                       VIS_NOISE <= img < VIS_LEGIT

Saída: resumo no stdout + relatório markdown em REPORT.md.
"""
import json
import os
import sys
from collections import defaultdict

# Resolve raiz do projeto e torna imports/vocab relativos resolvíveis
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from services.nlp_service import nlp_service  # noqa: E402

VOCAB = nlp_service._vocab
KNOWN_BRANDS = set(VOCAB.known_brands_for_detection)  # gatilho do gate (espelha o código real)

# Lista ampla só para ROTULAR ruído de concorrente (não afeta o gate)
COMPETITOR_TOKENS = {
    "hering", "lacoste", "tommy", "hilfiger", "reserva", "calvin", "klein",
    "colombo", "richards", "forum", "osklen", "ellus", "colcci", "malwee",
    "ralph", "lauren", "nike", "adidas", "puma", "oakley", "vans", "fila",
    "individual", "acostamento", "sergio", "kingsky",
}

HIST = "data/search_history.json"
VIS_LEGIT = 85.0   # img alto + marca ausente => legítimo de marca omitida (perda de cobertura)
VIS_NOISE = 60.0   # img baixo + marca ausente => provável marca/modelo errado (ganho precisão)
SPIKE_DIR = os.path.join("/".join(__file__.replace("\\", "/").split("/")[:-1]))


def clean(text: str) -> str:
    return nlp_service._clean_text(text or "")


def load_rows():
    data = json.load(open(HIST, encoding="utf-8"))
    cross = [v for v in data.values() if v.get("type") == "cross" and isinstance(v.get("results"), dict)]
    rows = []
    for v in cross:
        contract = v.get("results") or {}
        official = contract.get("search_query") or v.get("query") or ""
        official_words = set(clean(official).split())
        query_brands = official_words & KNOWN_BRANDS
        for it in (contract.get("results") or []):
            twords = set(clean(it.get("title") or "").split())
            brand_present = bool(query_brands & twords) if query_brands else True
            rows.append({
                "query": official,
                "query_brands": sorted(query_brands),
                "gate_applicable": bool(query_brands),
                "marketplace": it.get("marketplace"),
                "title": it.get("title") or "",
                "brand_present": brand_present,
                "img": float(it.get("image_match_score") or 0.0),
                "txt": float(it.get("text_match_score") or 0.0),
                "fin": float(it.get("final_match_score") or 0.0),
                "named_competitor": bool((twords & COMPETITOR_TOKENS) - query_brands),
            })
    return rows, len(cross)


def bucket(img: float) -> str:
    if img >= VIS_LEGIT:
        return "coverage_loss"
    if img < VIS_NOISE:
        return "precision_win"
    return "ambiguous"


def main():
    rows, n_jobs = load_rows()
    total = len(rows)
    applicable = [r for r in rows if r["gate_applicable"]]
    n_app = len(applicable)
    present = [r for r in applicable if r["brand_present"]]
    dropped = [r for r in applicable if not r["brand_present"]]  # gate rígido descartaria

    buckets = defaultdict(list)
    for r in dropped:
        buckets[bucket(r["img"])].append(r)

    named = [r for r in dropped if r["named_competitor"]]

    # por marketplace
    per_mkt = defaultdict(lambda: {"shown": 0, "dropped": 0, "cov_loss": 0, "prec_win": 0})
    for r in applicable:
        m = r["marketplace"]
        per_mkt[m]["shown"] += 1
        if not r["brand_present"]:
            per_mkt[m]["dropped"] += 1
            b = bucket(r["img"])
            if b == "coverage_loss":
                per_mkt[m]["cov_loss"] += 1
            elif b == "precision_win":
                per_mkt[m]["prec_win"] += 1

    def pct(a, b):
        return (100.0 * a / b) if b else 0.0

    # ---- stdout ----
    print(f"Jobs cross analisados: {n_jobs}")
    print(f"Itens exibidos (total): {total}")
    print(f"Itens com gate aplicável (query tem marca conhecida): {n_app} ({pct(n_app,total):.0f}%)")
    print(f"  - marca presente no título (mantidos): {len(present)} ({pct(len(present),n_app):.0f}%)")
    print(f"  - marca AUSENTE (gate rígido descartaria): {len(dropped)} ({pct(len(dropped),n_app):.0f}%)")
    print(f"      • GANHO DE PRECISÃO (img<{VIS_NOISE:.0f}): {len(buckets['precision_win'])}")
    print(f"      • PERDA DE COBERTURA (img>={VIS_LEGIT:.0f}): {len(buckets['coverage_loss'])}")
    print(f"      • AMBÍGUO ({VIS_NOISE:.0f}<=img<{VIS_LEGIT:.0f}): {len(buckets['ambiguous'])}")
    print(f"      • dos descartados, nomeiam concorrente explícito: {len(named)}")

    # ---- markdown report ----
    lines = []
    lines.append("# Spike 001 — Impacto do Gate Rígido de Marca (dados reais)\n")
    lines.append(f"- Jobs cross analisados: **{n_jobs}**")
    lines.append(f"- Itens exibidos (total): **{total}**")
    lines.append(f"- Limiares: PERDA_COBERTURA img>=`{VIS_LEGIT:.0f}` | GANHO_PRECISAO img<`{VIS_NOISE:.0f}`\n")
    lines.append("## Resultado do gate rígido (entre itens com gate aplicável)\n")
    lines.append("| Métrica | Itens | % do aplicável |")
    lines.append("|---|---|---|")
    lines.append(f"| Gate aplicável (query tem marca) | {n_app} | {pct(n_app,total):.0f}% do total |")
    lines.append(f"| Marca presente (mantidos) | {len(present)} | {pct(len(present),n_app):.0f}% |")
    lines.append(f"| Marca ausente (DESCARTADOS) | {len(dropped)} | {pct(len(dropped),n_app):.0f}% |")
    lines.append(f"| → Ganho de precisão (img<{VIS_NOISE:.0f}) | {len(buckets['precision_win'])} | {pct(len(buckets['precision_win']),n_app):.0f}% |")
    lines.append(f"| → Perda de cobertura (img>={VIS_LEGIT:.0f}) | {len(buckets['coverage_loss'])} | {pct(len(buckets['coverage_loss']),n_app):.0f}% |")
    lines.append(f"| → Ambíguo | {len(buckets['ambiguous'])} | {pct(len(buckets['ambiguous']),n_app):.0f}% |")
    lines.append(f"| Descartados que nomeiam concorrente | {len(named)} | {pct(len(named),len(dropped)):.0f}% dos descartados |\n")

    lines.append("## Por marketplace\n")
    lines.append("| Marketplace | Exibidos | Descartados | → Precisão | → Cobertura |")
    lines.append("|---|---|---|---|---|")
    for m, s in sorted(per_mkt.items(), key=lambda x: -x[1]["shown"]):
        lines.append(f"| {m} | {s['shown']} | {s['dropped']} | {s['prec_win']} | {s['cov_loss']} |")
    lines.append("")

    def sample_table(title, items, key=lambda r: -r["txt"], n=12):
        lines.append(f"## {title}\n")
        if not items:
            lines.append("_(nenhum)_\n")
            return
        lines.append("| txt | img | fin | marca? | concorrente? | título |")
        lines.append("|---|---|---|---|---|---|")
        for r in sorted(items, key=key)[:n]:
            t = (r["title"][:60]).replace("|", "/")
            lines.append(
                f"| {r['txt']:.0f} | {r['img']:.0f} | {r['fin']:.0f} | "
                f"{'sim' if r['brand_present'] else 'NÃO'} | "
                f"{'sim' if r['named_competitor'] else '-'} | {t} |"
            )
        lines.append("")

    sample_table("Amostra — GANHO DE PRECISÃO (descartados, visual baixo)", buckets["precision_win"])
    sample_table("Amostra — PERDA DE COBERTURA (descartados, visual alto)", buckets["coverage_loss"], key=lambda r: -r["img"])
    sample_table("Amostra — AMBÍGUOS (descartados, visual médio)", buckets["ambiguous"], key=lambda r: -r["img"])

    report_path = os.path.join(ROOT, ".planning", "spikes", "001-brand-gate-impact", "REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nRelatório escrito em: {report_path}")


if __name__ == "__main__":
    main()
