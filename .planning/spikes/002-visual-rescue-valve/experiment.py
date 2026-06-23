"""
Spike 002: Válvula de resgate visual sobre o gate rígido de marca.

Hipótese original: depois de aplicar o gate rígido de marca (descarta brand-absent), uma
"válvula" poderia RESGATAR os legítimos que apenas omitiram a marca, mantendo-os se o
image_match_score CLIP for alto (>= T).

Spike 001 levantou a suspeita de que isso é uma ARMADILHA: entre os itens brand-absent, os de
visual alto são dominados por concorrentes PARECIDOS (Hering, Sanders), não por Aramis legítimo.
Este spike varre thresholds T e quantifica quanto ruído a válvula readmitiria.

Métrica-chave: dos itens que a válvula resgataria (brand-absent, img>=T), quantos nomeiam um
concorrente explícito (= ruído que JAMAIS deveria voltar). Se a fração for alta, a válvula é
insegura — não distingue "mesmo produto, marca omitida" de "concorrente que se parece".
"""
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from services.nlp_service import nlp_service  # noqa: E402

VOCAB = nlp_service._vocab
KNOWN_BRANDS = set(VOCAB.known_brands_for_detection)
COMPETITOR_TOKENS = {
    "hering", "lacoste", "tommy", "hilfiger", "reserva", "calvin", "klein",
    "colombo", "richards", "forum", "osklen", "ellus", "colcci", "malwee",
    "ralph", "lauren", "nike", "adidas", "puma", "oakley", "vans", "fila",
    "individual", "acostamento", "sergio", "kingsky", "sanders", "syc",
}
HIST = "data/search_history.json"
THRESHOLDS = [80.0, 85.0, 90.0, 95.0]


def clean(text):
    return nlp_service._clean_text(text or "")


def load_brand_absent():
    data = json.load(open(HIST, encoding="utf-8"))
    cross = [v for v in data.values() if v.get("type") == "cross" and isinstance(v.get("results"), dict)]
    absent = []
    for v in cross:
        contract = v.get("results") or {}
        official = contract.get("search_query") or v.get("query") or ""
        query_brands = set(clean(official).split()) & KNOWN_BRANDS
        if not query_brands:
            continue
        for it in (contract.get("results") or []):
            twords = set(clean(it.get("title") or "").split())
            if query_brands & twords:
                continue  # marca presente — gate não toca
            absent.append({
                "title": it.get("title") or "",
                "img": float(it.get("image_match_score") or 0.0),
                "txt": float(it.get("text_match_score") or 0.0),
                "named_competitor": bool((twords & COMPETITOR_TOKENS) - query_brands),
            })
    return absent


def main():
    absent = load_brand_absent()
    n = len(absent)
    print(f"Itens brand-absent (que o gate rígido removeria): {n}\n")
    print(f"{'T (img>=)':>10} | {'resgatados':>10} | {'nomeiam concorrente':>20} | {'% ruído explícito':>18}")
    print("-" * 70)

    lines = ["# Spike 002 — Válvula de Resgate Visual\n",
             f"Itens brand-absent (que o gate rígido removeria): **{n}**\n",
             "## Varredura de threshold da válvula (resgatar se img >= T)\n",
             "| T (img>=) | resgatados | nomeiam concorrente | % ruído explícito |",
             "|---|---|---|---|"]

    for T in THRESHOLDS:
        rescued = [r for r in absent if r["img"] >= T]
        named = [r for r in rescued if r["named_competitor"]]
        nr = len(rescued)
        pct = (100.0 * len(named) / nr) if nr else 0.0
        print(f"{T:>10.0f} | {nr:>10} | {len(named):>20} | {pct:>17.0f}%")
        lines.append(f"| {T:.0f} | {nr} | {len(named)} | {pct:.0f}% |")

    lines.append("")
    # Amostra dos itens que a válvula resgataria no T mais alto (90)
    rescued90 = sorted([r for r in absent if r["img"] >= 90.0], key=lambda r: -r["img"])
    lines.append("## Amostra — itens resgatados com T=90 (deveriam ser Aramis legítimo?)\n")
    if rescued90:
        lines.append("| img | txt | concorrente? | título |")
        lines.append("|---|---|---|---|")
        for r in rescued90[:15]:
            t = r["title"][:60].replace("|", "/")
            lines.append(f"| {r['img']:.0f} | {r['txt']:.0f} | {'sim' if r['named_competitor'] else '?'} | {t} |")
    else:
        lines.append("_(nenhum item brand-absent atinge img>=90)_")
    lines.append("")

    report = os.path.join(ROOT, ".planning", "spikes", "002-visual-rescue-valve", "REPORT.md")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nRelatório: {report}")


if __name__ == "__main__":
    main()
