from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Gate D-08/D-10: spike isolado — NÃO importar de backend/ como efeito colateral
# e NÃO gravar arquivos dentro de backend/. Este arquivo vive SOMENTE em
# .planning/spikes/010-zara-product-price/ e não referencia nenhum módulo de backend.

SPIKE_DIR = Path(__file__).resolve().parent
REPORT_PATH = SPIKE_DIR / "REPORT.md"

# URL de busca pública Zara BR com filtro masculino (D-07 / CAT-01 — usar section=MAN, nunca o feminino)
ZARA_SEARCH_URL = "https://www.zara.com/br/pt/search?searchTerm={query}&section=MAN"

QUERIES = ["camiseta", "calça"]

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--mute-audio",
    "--no-first-run",
]

STEALTH_ARGS = CHROMIUM_ARGS + ["--disable-blink-features=AutomationControlled"]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
HEADERS = {
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


@dataclass
class ProbeResult:
    label: str
    url: str
    mode: str
    ok: bool = False
    status: Optional[int] = None
    final_url: str = ""
    title: str = ""
    html_bytes: int = 0
    blocked_signals: list[str] = field(default_factory=list)
    products: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""


def _new_context(browser: Any) -> Any:
    return browser.new_context(
        user_agent=USER_AGENT,
        java_script_enabled=True,
        viewport={"width": 1366, "height": 768},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
        extra_http_headers=HEADERS,
    )


def _detect_block(html: str, status: Optional[int]) -> list[str]:
    signals: list[str] = []
    lowered = html.lower()
    if status == 403:
        signals.append("http_status_403")
    if "access denied" in lowered:
        signals.append("access_denied_text")
    if "akamai" in lowered or "reference #" in lowered:
        signals.append("akamai_reference")
    if len(html.encode("utf-8")) < 1000:
        signals.append("html_below_1000_bytes")
    return signals


def _extract_jsonld_products(html: str) -> list[dict[str, Any]]:
    """Tenta extrair produtos de <script type="application/ld+json"> na página de busca.

    Investiga todos os blocos JSON-LD da página; procura por ItemList ou array de
    produtos (schema.org/Product). Armadilha 4: JSON-LD na home != JSON-LD na busca.
    """
    products: list[dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", type="application/ld+json")
        for script in scripts:
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            # Caso ItemList
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for item in data.get("itemListElement", []):
                    product = item.get("item", item)
                    parsed = _parse_jsonld_item(product)
                    if parsed:
                        products.append(parsed)
            # Caso Product direto
            elif isinstance(data, dict) and data.get("@type") == "Product":
                parsed = _parse_jsonld_item(data)
                if parsed:
                    products.append(parsed)
            # Caso lista de produtos
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        parsed = _parse_jsonld_item(item)
                        if parsed:
                            products.append(parsed)
    except Exception:  # noqa: BLE001 - spike: registrar falha sem crashar
        pass
    return products


def _parse_jsonld_item(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extrai title, url e preço de um nó JSON-LD de produto."""
    name = str(data.get("name") or "").strip()
    url = str(data.get("url") or "").strip()
    if not name or "zara.com/br" not in url:
        return None

    # Tenta extrair preço de offers
    price: Optional[float] = None
    offers = data.get("offers") or {}
    if isinstance(offers, dict):
        raw_price = offers.get("price") or offers.get("lowPrice")
        price = _parse_price(raw_price)
    elif isinstance(offers, list) and offers:
        raw_price = offers[0].get("price") or offers[0].get("lowPrice")
        price = _parse_price(raw_price)

    if price is None or price <= 0:
        return None

    image_url: Optional[str] = None
    image = data.get("image")
    if isinstance(image, str):
        image_url = image
    elif isinstance(image, list) and image:
        image_url = image[0] if isinstance(image[0], str) else None

    return {"title": name, "url": url, "price": price, "image_url": image_url}


def _parse_price(raw: Any) -> Optional[float]:
    """Converte string ou número para float, retorna None se inválido."""
    if raw is None:
        return None
    try:
        value = float(str(raw).replace(",", ".").strip())
        return value if value > 0 else None
    except (ValueError, TypeError):
        return None



def _extract_products_from_tiles(html: str) -> list[dict[str, Any]]:
    """Fallback: parsear tiles de produto via seletores CSS/BeautifulSoup.

    Armadilha 4: se JSON-LD e XHR não revelarem produtos, tenta parsing
    de HTML de tiles. A Zara usa classes CSS dinamicamente geradas; usa
    heurísticas baseadas em aria-labels e links de produto.
    """
    products: list[dict[str, Any]] = []
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Tenta localizar links de produto: hrefs que apontem para /br/pt/ com .html
        seen_urls: set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            href = str(a_tag.get("href", ""))
            if "zara.com/br" not in href and not href.startswith("/br/pt/"):
                continue
            if href.startswith("/br/pt/"):
                href = f"https://www.zara.com{href}"
            if ".html" not in href:
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Tenta extrair nome do texto do link ou aria-label
            label = str(a_tag.get("aria-label") or "").strip()
            if not label:
                label = " ".join(a_tag.get_text(separator=" ").split()).strip()
            if not label or len(label) < 3:
                continue

            # Tenta extrair preço de elemento vizinho
            parent = a_tag.parent or a_tag
            price_text = ""
            for price_el in parent.find_all(
                attrs={"class": lambda c: c and any("price" in str(x).lower() for x in c)}
            ):
                price_text = price_el.get_text(separator=" ")
                break

            price = _parse_price_text(price_text)
            products.append({"title": label, "url": href, "price": price or 0.0, "image_url": None})

            if len(products) >= 10:
                break
    except Exception:  # noqa: BLE001 - spike
        pass

    # Filtra apenas produtos com preço positivo para manter contrato de validade
    return [p for p in products if p.get("price", 0) > 0]


def _parse_price_text(text: str) -> Optional[float]:
    """Extrai o primeiro número de uma string de texto de preço (ex: 'R$ 199,99')."""
    import re
    text = text.replace(".", "").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if match:
        try:
            value = float(match.group())
            return value if value > 0 else None
        except ValueError:
            return None
    return None


def _is_valid_product(product: dict[str, Any]) -> bool:
    title = str(product.get("title") or "").strip()
    url = str(product.get("url") or "").strip()
    price = product.get("price")
    return bool(
        title
        and "zara.com/br" in url
        and isinstance(price, (int, float))
        and price > 0
    )


def _dedupe_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for product in products:
        url = str(product.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(product)
    return unique


def collect_zara_products(
    playwright: Any, query: str, round_label: str
) -> tuple[ProbeResult, list[dict[str, Any]]]:
    """Navega à busca pública da Zara BR com playwright-stealth e extrai produtos.

    Investiga em ordem de fallback (Armadilha 4):
      (a) JSON-LD com ItemList/Product
      (b) Interceptação de respostas de rede JSON
      (c) Parsing de tiles HTML via seletores CSS

    Retorna (ProbeResult, produtos_validos).
    """
    url = ZARA_SEARCH_URL.format(query=quote_plus(query))
    result = ProbeResult(label=f"zara-search-{query}-{round_label}", url=url, mode="stealth")
    browser = None
    context = None
    page = None
    products: list[dict[str, Any]] = []

    try:
        browser = playwright.chromium.launch(headless=True, args=STEALTH_ARGS)
        context = _new_context(browser)
        # Aplica playwright-stealth no contexto (D-06 — browser público stealth)
        Stealth().apply_stealth_sync(context)
        page = context.new_page()

        # Interceptação de rede: registrada antes do goto
        captured_json: list[dict[str, Any]] = []

        def on_response(response: Any) -> None:
            try:
                content_type = response.headers.get("content-type", "")
                if "application/json" not in content_type:
                    return
                resp_url = response.url.lower()
                if not any(kw in resp_url for kw in ("search", "product", "catalog", "items")):
                    return
                body = response.json()
                if isinstance(body, list):
                    captured_json.extend(body)
                elif isinstance(body, dict):
                    for key in ("products", "items", "results"):
                        value = body.get(key)
                        if isinstance(value, list):
                            captured_json.extend(value)
                            break
                    nested = body.get("data") or {}
                    if isinstance(nested, dict):
                        for key in ("products", "items", "results"):
                            value = nested.get(key)
                            if isinstance(value, list):
                                captured_json.extend(value)
                                break
            except Exception:  # noqa: BLE001
                pass

        page.on("response", on_response)

        response = page.goto(url, wait_until="domcontentloaded", timeout=40000)
        time.sleep(2.5)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:  # noqa: BLE001 - networkidle pode timeout em SPAs pesadas
            pass

        html = page.content()

        result.ok = True
        result.status = response.status if response else None
        result.final_url = page.url
        result.title = page.title()
        result.html_bytes = len(html.encode("utf-8"))
        result.blocked_signals = _detect_block(html, result.status)

        if not result.blocked_signals:
            # (a) JSON-LD
            jsonld_products = _extract_jsonld_products(html)
            valid_jsonld = [p for p in jsonld_products if _is_valid_product(p)]
            if valid_jsonld:
                products = _dedupe_products(valid_jsonld)

            # (b) Rede XHR
            if not products:
                network_products: list[dict[str, Any]] = []
                for item in captured_json:
                    if not isinstance(item, dict):
                        continue
                    name = str(
                        item.get("name")
                        or item.get("title")
                        or item.get("productName")
                        or ""
                    ).strip()
                    item_url = str(
                        item.get("url") or item.get("link") or item.get("href") or ""
                    ).strip()
                    if item_url and not item_url.startswith("http"):
                        item_url = f"https://www.zara.com/br{item_url}"
                    raw_price = (
                        item.get("price")
                        or item.get("price_full")
                        or item.get("salePrice")
                        or item.get("regularPrice")
                    )
                    price = _parse_price(raw_price)
                    if name and "zara.com/br" in item_url and price and price > 0:
                        network_products.append(
                            {"title": name, "url": item_url, "price": price, "image_url": None}
                        )
                if network_products:
                    products = _dedupe_products(network_products)

            # (c) Tiles HTML
            if not products:
                tile_products = _extract_products_from_tiles(html)
                if tile_products:
                    products = _dedupe_products(tile_products)

        result.products = products

    except PlaywrightTimeoutError as exc:
        result.error = f"timeout: {exc}"
    except Exception as exc:  # noqa: BLE001 - spike deve registrar falha sem crashar
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        for handle in (page, context, browser):
            try:
                if handle:
                    handle.close()
            except Exception:  # noqa: BLE001
                pass

    return result, products


def choose_verdict(first_round: list[dict[str, Any]], second_round: list[dict[str, Any]]) -> str:
    """Avalia o gate D-05.

    GO        → ≥3 produtos reais (título + URL zara.com/br + preço positivo)
                em AMBAS as rodadas (evidência estável e reprodutível).
    GO_TECHNICAL → ≥1 produto em pelo menos uma rodada mas sem repetição estável
                   (pode ser GO condicionado a mais investigação).
    NO-GO     → 0 produtos em ambas as rodadas (bloqueio confirmado).
    """
    if len(first_round) >= 3 and len(second_round) >= 3:
        return "GO"
    if first_round or second_round:
        return "GO_TECHNICAL"
    return "NO-GO"


def product_table(products: list[dict[str, Any]]) -> str:
    if not products:
        return "- Nenhum produto real com titulo nao vazio + URL zara.com/br + preco positivo.\n"
    lines = ["| Titulo | URL | Preco |", "|---|---|---|"]
    for product in products:
        title = str(product.get("title") or "").replace("|", "\\|")
        url = str(product.get("url") or "")
        price = product.get("price", "")
        lines.append(f"| {title} | {url} | {price} |")
    return "\n".join(lines) + "\n"


def probe_table(probes: list[ProbeResult]) -> str:
    lines = [
        "| Probe | Modo | Status | Bytes | Final URL | Bloqueio | Produtos | Erro |",
        "|---|---|---:|---:|---|---|---:|---|",
    ]
    for probe in probes:
        block = ", ".join(probe.blocked_signals) or "-"
        error = (probe.error or "-").replace("|", "\\|")
        final_url = (probe.final_url or "-").replace("|", "\\|")
        n_products = len(probe.products)
        lines.append(
            f"| {probe.label} | {probe.mode} | {probe.status or '-'} | {probe.html_bytes} | "
            f"{final_url} | {block} | {n_products} | {error} |"
        )
    return "\n".join(lines) + "\n"


def write_report(
    first_query: str,
    first_probes: list[ProbeResult],
    first_round: list[dict[str, Any]],
    second_query: str,
    second_probes: list[ProbeResult],
    second_round: list[dict[str, Any]],
    verdict: str,
    exception: str = "",
) -> None:
    generated = datetime.now(timezone.utc).isoformat()

    next_step_map = {
        "GO": (
            "Executar Plano 03: construir `InditexEngine` em `backend/services/engines/inditex_engine.py`, "
            "adicionar branch `engine_type == 'inditex'` em `factory.py`, onboardar Zara em `brands.json` "
            "e executar smoke test de busca real."
        ),
        "GO_TECHNICAL": (
            "Investigar antes de executar Plano 03: ≥1 produto extraido mas sem estabilidade em ambas as rodadas. "
            "Opções: (a) ajustar seletor/fallback de extração; (b) reexecutar spike com mais tentativas; "
            "(c) avaliar se GO_TECHNICAL é suficiente para avançar ao Plano 03 com ressalvas. "
            "Decisão do operador necessária antes de commitar engine."
        ),
        "NO-GO": (
            "Parar execução do Plano 03. Registrar veredito NO-GO com evidência (técnicas testadas + "
            "assinatura do bloqueio) e deferir COMP-07 ao backlog. "
            "Nenhum código de engine Zara deve ser commitado."
        ),
    }
    next_step = next_step_map.get(verdict, next_step_map["NO-GO"])

    all_products = _dedupe_products(first_round + second_round)

    report = f"""# Spike 010 - Zara: viabilidade de extração pública de produto+preço

Gerado em: {generated}

## Veredito

**`{verdict}`**

Criterio D-05: GO = >=3 produtos reais (titulo + URL zara.com/br + preco positivo) em AMBAS as rodadas.

## Rodada 1 — query: `{first_query}`

### Probes

{probe_table(first_probes)}

### Produtos extraidos

{product_table(first_round)}

## Rodada 2 — query: `{second_query}`

### Probes

{probe_table(second_probes)}

### Produtos extraidos

{product_table(second_round)}

## Todos os produtos (consolidado, sem duplicatas)

{product_table(all_products)}

## Tecnicas testadas

- **Browser stealth publico:** Chromium headless + `playwright_stealth.Stealth().apply_stealth_sync(context)`, user-agent desktop Chrome 125, locale `pt-BR`, timezone `America/Sao_Paulo`, viewport 1366x768, headers Accept-Language/Sec-CH-UA coerentes.
- **URL de busca:** `{ZARA_SEARCH_URL}` (section=MAN — filtro masculino D-07/CAT-01).
- **Aguardar carregamento:** `wait_until="domcontentloaded"` + sleep 2.5s + `networkidle` (timeout 8s).
- **Fallback (a) JSON-LD:** Todos os `<script type="application/ld+json">` da pagina de busca inspecionados (ItemList, Product, lista).
- **Fallback (b) Intercepção de rede:** Respostas `application/json` com keywords `search/product/catalog/items` na URL capturadas durante navegação.
- **Fallback (c) Tiles HTML:** BeautifulSoup: links `/br/pt/*.html` em `zara.com/br` + texto aria-label + elemento com classe `price`.
- **Baixa frequencia:** Apenas 2 rodadas, probes sequenciais, sleeps entre tentativas. Sem concorrencia.

## Evidencia de isolamento

- `experiment.py` vive exclusivamente em `.planning/spikes/010-zara-product-price/`.
- Nenhum modulo de `backend/` foi importado (gate D-08/D-10).
- Nenhum arquivo foi gravado dentro de `backend/`.

## Decisao do gate (COMP-07)

{next_step}

## Proibicoes respeitadas

- Nao foi usado proxy residencial pago, gateway de scraping, CAPTCHA solving, browser headed/manual, perfil persistente real, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado.
- O spike nao alterou `backend/` nem `backend/data/brands.json`.
- Filtro masculino `section=MAN` respeitado em todas as probes (D-07 / CAT-01).
"""
    if exception:
        report += f"\n## Excecao do script\n\n```text\n{exception}\n```\n"

    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    first_probes: list[ProbeResult] = []
    second_probes: list[ProbeResult] = []
    first_round: list[dict[str, Any]] = []
    second_round: list[dict[str, Any]] = []
    first_query = QUERIES[0]
    second_query = QUERIES[1] if len(QUERIES) > 1 else QUERIES[0]
    verdict = "NO-GO"
    exception = ""

    try:
        with sync_playwright() as playwright:
            # Rodada 1 — tenta as duas queries, usa a que retornar mais produtos
            for query in QUERIES:
                probe, products = collect_zara_products(playwright, query, "round1")
                first_probes.append(probe)
                if len(products) > len(first_round):
                    first_round = products
                    first_query = query
                time.sleep(2.0)

            # Rodada 2 — repete com a query que obteve mais produtos (ou a segunda se empate)
            for query in QUERIES:
                probe, products = collect_zara_products(playwright, query, "round2")
                second_probes.append(probe)
                if len(products) > len(second_round):
                    second_round = products
                    second_query = query
                time.sleep(2.0)

            verdict = choose_verdict(first_round, second_round)

    except Exception as exc:  # noqa: BLE001 - always write report
        exception = f"{type(exc).__name__}: {exc}"
    finally:
        write_report(
            first_query,
            first_probes,
            first_round,
            second_query,
            second_probes,
            second_round,
            verdict,
            exception,
        )

    print(
        json.dumps(
            {
                "verdict": verdict,
                "first_round_count": len(first_round),
                "second_round_count": len(second_round),
                "report": str(REPORT_PATH),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
