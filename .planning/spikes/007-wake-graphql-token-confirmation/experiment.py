"""
Spike 007 — Wake GraphQL Token Confirmation

Valida empiricamente o fluxo GraphQL + TCS-Access-Token da Wake contra:
  - Alvo primário: Richards (www.richards.com.br)
  - Alvo fallback: Shop2gether (www.shop2gether.com.br)

Confirma as suposicoes A1-A6 do 32-RESEARCH.md e produz REPORT.md com veredito GO/NO-GO.

GO exige >= 1 produto com titulo + URL + preco retornado via GraphQL + token (D-02).

Execucao (da raiz do repo):
    python .planning/spikes/007-wake-graphql-token-confirmation/experiment.py
"""
import asyncio
import os
import re
import sys
from typing import Optional

# Bootstrap: resolve raiz do repo (spike fica 3 niveis abaixo da raiz)
# .planning/spikes/007-wake-graphql-token-confirmation/ -> 3 niveis acima = raiz
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
# Os modulos do projeto (core/, services/) ficam em backend/
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.chdir(ROOT)

from core.session_manager import SessionManager  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes de modulo
# ---------------------------------------------------------------------------

GRAPHQL_ENDPOINT = "https://storefront-api.fbits.net/graphql"

# Regex principal: padrao SDK Wake (clientConfig.storefrontAccessToken)
_TOKEN_RE = re.compile(
    r"""storefrontAccessToken\s*:\s*['"]([^'"]+)['"]""",
    re.IGNORECASE,
)

# Regex fallback: qualquer ocorrencia de token tcs_ em scripts inline
_TOKEN_FALLBACK_RE = re.compile(
    r"""['"]?(tcs_[a-zA-Z0-9_]+)['"]?""",
)

# Query GraphQL de busca Wake (Padrao 4 do RESEARCH)
# Usa variaveis GraphQL ($q, $first) — NUNCA interpolacao de string (mitigacao Tampering T-32-02)
_GRAPHQL_QUERY = """
query WakeSearch($q: String!, $first: Int!) {
  search(query: $q) {
    products(first: $first) {
      edges {
        node {
          productName
          aliasComplete
          prices {
            price
            listPrice
          }
          images {
            url
          }
          available
        }
      }
    }
  }
}
"""

# Alvos: Richards primario, Shop2gether fallback (D-01)
TARGETS = [
    ("Richards", "www.richards.com.br"),
    ("Shop2gether", "www.shop2gether.com.br"),
]

SPIKE_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Extracao do token
# ---------------------------------------------------------------------------

def extract_token_from_html(html: str) -> Optional[str]:
    """
    Extrai o storefrontAccessToken do inline script do SDK Wake.

    Estrategia primaria: regex 'storefrontAccessToken : "..."'
    Estrategia fallback: regex 'tcs_[a-zA-Z0-9_]+' em qualquer <script> inline

    Retorna None se nao encontrado — caller trata como ausencia de token.
    """
    # Estrategia primaria
    match = _TOKEN_RE.search(html)
    if match:
        return match.group(1)

    # Estrategia fallback: buscar em scripts inline
    script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    for block in script_blocks:
        fb = _TOKEN_FALLBACK_RE.search(block)
        if fb:
            return fb.group(1)

    return None


def mask_token(token: str) -> str:
    """Mascara o token: mostra apenas os primeiros 12 chars + '...' (T-32-03)."""
    if len(token) <= 12:
        return token[:4] + "..."
    return token[:12] + "..."


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------

async def try_target(name: str, domain: str) -> dict:
    """
    Tenta extrair o token e bater no endpoint GraphQL para um alvo.

    Retorna dict com:
      - success: bool
      - token_found: bool
      - token_prefix: str (mascarado)
      - token_strategy: str
      - token_source_url: str
      - http_status_home: int
      - graphql_status: int
      - products: list
      - fields_confirmed: dict (A2/A3/A4)
      - error: str (se falhou)
      - raw_price_sample: valor bruto de prices.price (A4)
    """
    result = {
        "name": name,
        "domain": domain,
        "success": False,
        "token_found": False,
        "token_prefix": "",
        "token_strategy": "",
        "token_source_url": "",
        "http_status_home": None,
        "graphql_status": None,
        "products": [],
        "fields_confirmed": {
            "productName": False,
            "aliasComplete": False,
            "prices_price": False,
            "images_url": False,
            "available": False,
        },
        "raw_price_sample": None,
        "error": "",
    }

    home_url = f"https://{domain}"
    print(f"\n[{name}] Tentando extrair token de {home_url}...")

    try:
        session = await SessionManager.get_session()

        # Passo 1: GET da home page com allow_redirects=False (mitigacao T-32-01 Open Redirect)
        async with session.get(home_url, allow_redirects=False) as resp:
            result["http_status_home"] = resp.status
            print(f"[{name}] GET {home_url} -> HTTP {resp.status}")

            if resp.status in (301, 302, 307, 308):
                # Redirect: tentar com https:// explicitamente (alguns sites redirecionam www para sem www)
                location = resp.headers.get("Location", "")
                print(f"[{name}] Redirect para: {location} — tentando URL final diretamente")
                # Tentar seguir o redirect manualmente (apenas 1 nivel) para obter o HTML
                async with session.get(location, allow_redirects=False) as resp2:
                    result["http_status_home"] = resp2.status
                    print(f"[{name}] GET {location} -> HTTP {resp2.status}")
                    html = await resp2.text(errors="replace")
            else:
                html = await resp.text(errors="replace")

        # Passo 2: Extrair o token via regex
        token = extract_token_from_html(html)

        if token:
            result["token_found"] = True
            result["token_prefix"] = mask_token(token)
            result["token_source_url"] = home_url
            # Determinar estrategia usada
            if _TOKEN_RE.search(html):
                result["token_strategy"] = "regex storefrontAccessToken (primaria)"
            else:
                result["token_strategy"] = "regex tcs_[a-zA-Z0-9_]+ em script inline (fallback)"
            print(f"[{name}] Token encontrado! Prefixo: {result['token_prefix']} | Estrategia: {result['token_strategy']}")
        else:
            result["error"] = "Token nao encontrado no HTML da home page (A5 falhou)"
            print(f"[{name}] FALHA: Token nao encontrado. {result['error']}")
            return result

        # Passo 3: POST GraphQL com variaveis (mitigacao T-32-02 Tampering)
        print(f"[{name}] Enviando query GraphQL para {GRAPHQL_ENDPOINT}...")
        graphql_body = {
            "query": _GRAPHQL_QUERY,
            "variables": {"q": "camisa", "first": 5},
        }
        headers = {
            "TCS-Access-Token": token,  # token completo no header (nunca no log)
            "Content-Type": "application/json",
        }

        async with session.post(GRAPHQL_ENDPOINT, json=graphql_body, headers=headers) as gresp:
            result["graphql_status"] = gresp.status
            print(f"[{name}] POST {GRAPHQL_ENDPOINT} -> HTTP {gresp.status}")

            if gresp.status != 200:
                result["error"] = f"GraphQL retornou HTTP {gresp.status} (A1 falhou — token invalido ou nao aceito)"
                print(f"[{name}] FALHA: {result['error']}")
                return result

            data = await gresp.json(content_type=None)

        # Passo 4: Parsear a resposta GraphQL
        errors = data.get("errors")
        if errors:
            result["error"] = f"GraphQL retornou erros: {errors} (A1 ou A6 falhou)"
            print(f"[{name}] FALHA: {result['error']}")
            return result

        # Navegar na estrutura data.search.products.edges[].node
        search_data = data.get("data", {}).get("search", {})
        products_data = search_data.get("products", {})
        edges = products_data.get("edges", [])

        print(f"[{name}] Produtos retornados: {len(edges)}")

        if not edges:
            result["error"] = "GraphQL retornou 0 produtos (A6 falhou — possivelmente reCAPTCHA/sessao)"
            print(f"[{name}] FALHA: {result['error']}")
            return result

        # Confirmar campos A2-A4 no primeiro produto
        parsed_products = []
        for edge in edges:
            node = edge.get("node", {})

            product_name = node.get("productName")
            alias_complete = node.get("aliasComplete")
            prices = node.get("prices", {})
            price = prices.get("price") if prices else None
            images = node.get("images", [])
            image_url = images[0].get("url") if images else None
            available = node.get("available")

            # Montar URL completa (Armadilha 2: aliasComplete pode ser relativo)
            if alias_complete:
                if alias_complete.startswith("http"):
                    product_url = alias_complete
                else:
                    product_url = f"https://{domain}/{alias_complete.lstrip('/')}"
            else:
                product_url = None

            parsed_products.append({
                "productName": product_name,
                "aliasComplete": alias_complete,
                "product_url": product_url,
                "price_raw": price,
                "image_url": image_url,
                "available": available,
            })

            # Confirmar campos (A2, A3, A4)
            if product_name:
                result["fields_confirmed"]["productName"] = True
            if alias_complete is not None:
                result["fields_confirmed"]["aliasComplete"] = True
            if price is not None:
                result["fields_confirmed"]["prices_price"] = True
                if result["raw_price_sample"] is None:
                    result["raw_price_sample"] = price
            if image_url:
                result["fields_confirmed"]["images_url"] = True
            if available is not None:
                result["fields_confirmed"]["available"] = True

        result["products"] = parsed_products

        # Verificar se temos GO: >= 1 produto com titulo + URL + preco (D-02)
        go_products = [
            p for p in parsed_products
            if p["productName"] and p["product_url"] and p["price_raw"] is not None
        ]

        if go_products:
            result["success"] = True
            print(f"[{name}] GO! {len(go_products)} produto(s) com titulo+URL+preco confirmados.")
            print(f"[{name}] Exemplo: '{go_products[0]['productName']}' | Preco: {go_products[0]['price_raw']}")
        else:
            result["error"] = "Produtos retornados mas sem titulo+URL+preco simultaneos (D-02 nao atendido)"
            print(f"[{name}] FALHA: {result['error']}")

    except Exception as exc:
        result["error"] = f"Excecao inesperada: {type(exc).__name__}: {exc}"
        print(f"[{name}] EXCECAO: {result['error']}")

    return result


async def main():
    """Executa o spike contra todos os alvos e gera REPORT.md."""
    print("=" * 60)
    print("Spike 007 — Wake GraphQL Token Confirmation")
    print(f"Endpoint: {GRAPHQL_ENDPOINT}")
    print(f"Alvos: {[t[0] for t in TARGETS]}")
    print("=" * 60)

    go_result = None
    all_results = []

    for name, domain in TARGETS:
        r = await try_target(name, domain)
        all_results.append(r)
        if r["success"]:
            go_result = r
            print(f"\n[SPIKE] GO obtido com '{name}' — parando apos primeiro sucesso.")
            break

    # Fechar sessao
    await SessionManager.close_session()

    # Determinar veredito
    if go_result:
        verdict = "GO"
        verdict_detail = (
            f">= 1 produto com titulo+URL+preco retornado via GraphQL+token "
            f"(alvo: {go_result['name']})"
        )
    else:
        verdict = "NO-GO"
        reasons = [r["error"] for r in all_results if r["error"]]
        verdict_detail = " | ".join(reasons) if reasons else "Nenhum alvo retornou produtos validos"

    # Resumo no stdout
    print("\n" + "=" * 60)
    print(f"VEREDITO: {verdict}")
    print(f"Detalhe: {verdict_detail}")
    print("=" * 60)

    if go_result:
        print(f"\nAlvo testado com sucesso: {go_result['name']} ({go_result['domain']})")
        print(f"Token prefix: {go_result['token_prefix']} (mascara)")
        print(f"HTTP home: {go_result['http_status_home']}")
        print(f"HTTP GraphQL: {go_result['graphql_status']}")
        print(f"Produtos retornados: {len(go_result['products'])}")
        print(f"Campos confirmados: {go_result['fields_confirmed']}")
        print(f"Preco (sample bruto): {go_result['raw_price_sample']}")

    # Escrever REPORT.md
    _write_report(verdict, go_result, all_results)

    print(f"\nREPORT.md escrito em: {os.path.join(SPIKE_DIR, 'REPORT.md')}")


def _write_report(verdict: str, go_result: Optional[dict], all_results: list):
    """Escreve o REPORT.md com veredito explícito e evidencia estruturada."""

    lines = []
    lines.append("# Spike 007 — Wake GraphQL Token Confirmation")
    lines.append("")
    lines.append("## Veredito")

    if verdict == "GO":
        lines.append(f"**GO**")
        lines.append("")
        lines.append(
            f">= 1 produto com titulo + URL + preco retornado via GraphQL com header "
            f"`TCS-Access-Token` (D-02 atendido). Alvo: **{go_result['name']}**."
        )
    else:
        lines.append("**NO-GO**")
        lines.append("")
        reasons = [r["error"] for r in all_results if r["error"]]
        for r in reasons:
            lines.append(f"- {r}")

    lines.append("")
    lines.append("## Evidencia")
    lines.append("")

    if go_result:
        lines.append(f"- **Endpoint:** `{GRAPHQL_ENDPOINT}`")
        lines.append(
            f"- **Header:** `TCS-Access-Token: {go_result['token_prefix']}` "
            f"(extraido de: `{go_result['token_source_url']}`)"
        )
        lines.append(f"- **Estrategia de extracao:** {go_result['token_strategy']}")
        lines.append(f"- **HTTP status (home page):** {go_result['http_status_home']}")
        lines.append(f"- **HTTP status (GraphQL):** {go_result['graphql_status']}")
        lines.append(f"- **Query:** `search(query: \"camisa\", first: 5)` via variaveis GraphQL")
        lines.append(f"- **Produtos retornados:** {len(go_result['products'])}")
        lines.append("")

        # Mostrar ate 3 produtos como evidencia
        lines.append("### Produtos extraidos (amostra)")
        lines.append("")
        sample = go_result["products"][:3]
        for i, p in enumerate(sample, 1):
            lines.append(f"**Produto {i}:**")
            lines.append(f"- productName: `{p['productName']}`")
            lines.append(f"- aliasComplete (raw): `{p['aliasComplete']}`")
            lines.append(f"- URL construida: `{p['product_url']}`")
            lines.append(f"- prices.price (raw): `{p['price_raw']}`")
            lines.append(f"- images.url: `{p['image_url']}`")
            lines.append(f"- available: `{p['available']}`")
            lines.append("")
    else:
        lines.append("Nenhum alvo retornou evidencia valida.")
        lines.append("")
        for r in all_results:
            lines.append(f"### {r['name']} ({r['domain']})")
            lines.append(f"- HTTP status (home): {r['http_status_home']}")
            lines.append(f"- HTTP status (GraphQL): {r['graphql_status']}")
            lines.append(f"- Token encontrado: {r['token_found']}")
            lines.append(f"- Erro: {r['error']}")
            lines.append("")

    lines.append("## Campos confirmados")
    lines.append("")
    lines.append("| Campo | Disponivel | Valor exemplo |")
    lines.append("|-------|-----------|---------------|")

    if go_result:
        fc = go_result["fields_confirmed"]
        sample_prod = go_result["products"][0] if go_result["products"] else {}

        productName_ex = sample_prod.get("productName", "-") or "-"
        alias_ex = sample_prod.get("aliasComplete", "-") or "-"
        price_ex = sample_prod.get("price_raw", "-")
        image_ex = sample_prod.get("image_url", "-") or "-"
        available_ex = sample_prod.get("available", "-")

        lines.append(f"| productName | {'sim' if fc['productName'] else 'nao'} | `{str(productName_ex)[:60]}` |")
        lines.append(f"| aliasComplete | {'sim' if fc['aliasComplete'] else 'nao'} | `{str(alias_ex)[:60]}` |")
        lines.append(f"| prices.price | {'sim' if fc['prices_price'] else 'nao'} | `{price_ex}` |")
        lines.append(f"| images.url | {'sim' if fc['images_url'] else 'nao'} | `{str(image_ex)[:60]}` |")
        lines.append(f"| available | {'sim' if fc['available'] else 'nao'} | `{available_ex}` |")
    else:
        lines.append("| productName | nao confirmado | — |")
        lines.append("| aliasComplete | nao confirmado | — |")
        lines.append("| prices.price | nao confirmado | — |")
        lines.append("| images.url | nao confirmado | — |")
        lines.append("| available | nao confirmado | — |")

    lines.append("")
    lines.append("## Formato do preco")
    lines.append("")

    if go_result and go_result["raw_price_sample"] is not None:
        price_val = go_result["raw_price_sample"]
        # Heuristica: se > 10000 pode ser centavos; se < 10000 e um produto de moda, provavelmente reais
        if isinstance(price_val, (int, float)) and price_val < 10000:
            fmt_verdict = "CONFIRMADO — float em reais (valor abaixo de 10000, compativel com preco de produto de moda)"
        elif isinstance(price_val, (int, float)) and price_val >= 10000:
            fmt_verdict = "POSSIVELMENTE EM CENTAVOS — valor >= 10000; dividir por 100 se necessario"
        else:
            fmt_verdict = "INDETERMINADO"
        lines.append(f"- Valor bruto retornado pela API: `{price_val}`")
        lines.append(f"- Unidade: **{fmt_verdict}**")
        lines.append(f"- Resolucao A4: {'CONFIRMADO (float em reais)' if price_val < 10000 else 'A VERIFICAR (possivelmente centavos)'}")
    else:
        lines.append("- Nao determinado (nenhum produto retornado com preco)")
        lines.append("- Resolucao A4: NAO CONFIRMADO")

    lines.append("")
    lines.append("## Token auto-extraido")
    lines.append("")

    target_with_token = next((r for r in all_results if r["token_found"]), None)
    if target_with_token:
        lines.append(f"- **Estrategia:** {target_with_token['token_strategy']}")
        lines.append(f"- **Token encontrado em:** `{target_with_token['token_source_url']}`")
        lines.append(f"- **Prefixo observado:** `{target_with_token['token_prefix']}` (mascara — token completo omitido, T-32-03)")
        lines.append(f"- **Resolucao A1:** {'CONFIRMADO — token extraido aceito pelo endpoint GraphQL' if go_result else 'TOKEN EXTRAIDO MAS NAO VALIDADO pelo GraphQL'}")
        lines.append(f"- **Resolucao A5:** {'CONFIRMADO — Richards usa padrao SDK Wake (storefrontAccessToken no HTML)' if target_with_token['name'] == 'Richards' and target_with_token['token_strategy'].startswith('regex storefrontAccessToken') else 'PARCIAL — ver estrategia acima'}")
    else:
        lines.append("- Token nao encontrado em nenhum alvo")
        lines.append("- Resolucao A1: NAO CONFIRMADO")
        lines.append("- Resolucao A5: FALHOU — Richards nao expoe storefrontAccessToken no HTML")

    lines.append("")
    lines.append("## Alvo testado")
    lines.append("")

    for r in all_results:
        marker = "x" if r["success"] else " "
        status_note = "GO — sucesso" if r["success"] else f"Falhou: {r['error'][:80] if r['error'] else 'erro desconhecido'}"
        lines.append(f"- [{marker}] {r['name']} ({r['domain']}) — {status_note}")

    lines.append("")
    lines.append("## Resolucao das suposicoes A1-A6")
    lines.append("")
    lines.append("| # | Suposicao | Resultado |")
    lines.append("|---|-----------|-----------|")

    if go_result:
        fc = go_result["fields_confirmed"]
        target_with_tok = next((r for r in all_results if r["token_found"]), None)
        a1 = "CONFIRMADO" if go_result else "FALHOU"
        a2 = "CONFIRMADO" if fc["aliasComplete"] else "FALHOU — aliasComplete ausente em search.products.edges.node"
        a3 = "CONFIRMADO" if fc["images_url"] else "FALHOU — images.url ausente em search.products.edges.node"
        price_val = go_result["raw_price_sample"]
        a4 = "CONFIRMADO (float < 10000, interpretado como reais)" if (price_val is not None and price_val < 10000) else ("INDETERMINADO" if price_val is None else f"A VERIFICAR (valor={price_val})")
        a5_target = target_with_tok["name"] if target_with_tok else "nenhum"
        a5_strat = target_with_tok["token_strategy"] if target_with_tok else "—"
        a5 = f"CONFIRMADO ({a5_target}: {a5_strat})" if target_with_tok and target_with_tok["name"] == "Richards" else f"PARCIAL (confirmado apenas em {a5_target})" if target_with_tok else "FALHOU"
        a6 = "CONFIRMADO — busca retornou produtos sem reCAPTCHA ou sessao adicional"
    else:
        a1 = "FALHOU"
        a2 = "NAO CONFIRMADO"
        a3 = "NAO CONFIRMADO"
        a4 = "NAO CONFIRMADO"
        a5 = "FALHOU" if not any(r["token_found"] for r in all_results) else "PARCIAL (token extraido mas nao validado pelo GraphQL)"
        a6 = "FALHOU — nenhum produto retornado"

    lines.append(f"| A1 | storefrontAccessToken == TCS-Access-Token aceito pelo GraphQL | {a1} |")
    lines.append(f"| A2 | aliasComplete disponivel em search.products.edges.node | {a2} |")
    lines.append(f"| A3 | images.url disponivel em search.products.edges.node | {a3} |")
    lines.append(f"| A4 | prices.price em reais como float | {a4} |")
    lines.append(f"| A5 | Richards expoe storefrontAccessToken no HTML (padrao SDK Wake) | {a5} |")
    lines.append(f"| A6 | Busca nao exige reCAPTCHA/sessao alem do TCS-Access-Token | {a6} |")

    lines.append("")

    report_path = os.path.join(SPIKE_DIR, "REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
