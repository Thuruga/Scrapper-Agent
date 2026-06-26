from __future__ import annotations

import json
import sys
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

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from services.engines.sfcc_parser import parse_pdp, parse_search_results  # noqa: E402

SPIKE_DIR = Path(__file__).resolve().parent
REPORT_PATH = SPIKE_DIR / "REPORT.md"

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
    sfcc_signals: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
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


def _detect_sfcc(html: str) -> list[str]:
    lowered = html.lower()
    signals: list[str] = []
    if "demandware.static" in lowered or "on/demandware" in lowered:
        signals.append("demandware_marker")
    if "application/ld+json" in lowered and '"product' in lowered:
        signals.append("jsonld_product_marker")
    if "lacoste" in lowered:
        signals.append("lacoste_text")
    return signals


def _extract_products_from_html(html: str, domain: str, limit: int = 3) -> tuple[list[str], list[dict[str, Any]]]:
    candidates = parse_search_results(html, domain)
    products: list[dict[str, Any]] = []

    parsed = parse_pdp(html, f"https://www.{domain}/")
    if _is_valid_product(parsed, domain):
        products.append(_compact_product(parsed))

    return candidates[:limit], products[:limit]


def _is_valid_product(product: Optional[dict[str, Any]], domain: str) -> bool:
    if not product:
        return False
    url = str(product.get("url") or "")
    return bool(
        product.get("raw_title")
        and domain in url
        and isinstance(product.get("price_full"), (int, float))
        and product.get("price_full") > 0
    )


def _compact_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": product.get("raw_title"),
        "url": product.get("url"),
        "price": product.get("price_full"),
        "image_url": product.get("image_url"),
    }


def fetch_page(playwright: Any, url: str, label: str, mode: str, timeout_ms: int = 35000) -> ProbeResult:
    result = ProbeResult(label=label, url=url, mode=mode)
    browser = None
    context = None
    page = None
    try:
        args = STEALTH_ARGS if mode == "stealth" else CHROMIUM_ARGS
        browser = playwright.chromium.launch(headless=True, args=args)
        context = _new_context(browser)
        page = context.new_page()
        if mode == "stealth":
            Stealth().apply_stealth_sync(context)
        else:
            page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
                """
            )

        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        time.sleep(2.5 if mode == "stealth" else 1.0)
        html = page.content()
        result.ok = True
        result.status = response.status if response else None
        result.final_url = page.url
        result.title = page.title()
        result.html_bytes = len(html.encode("utf-8"))
        result.blocked_signals = _detect_block(html, result.status)
        result.sfcc_signals = _detect_sfcc(html)
        if "lacoste.com.br" in url:
            result.candidates, result.products = _extract_products_from_html(html, "lacoste.com.br")
        return result
    except PlaywrightTimeoutError as exc:
        result.error = f"timeout: {exc}"
        return result
    except Exception as exc:  # noqa: BLE001 - spike must record failures instead of crashing
        result.error = f"{type(exc).__name__}: {exc}"
        return result
    finally:
        for handle in (page, context, browser):
            try:
                if handle:
                    handle.close()
            except Exception:
                pass


def fetch_product(playwright: Any, url: str, mode: str = "stealth") -> Optional[dict[str, Any]]:
    page_result = fetch_page(playwright, url, f"lacoste-pdp:{url}", mode)
    if page_result.error or page_result.blocked_signals:
        return None
    try:
        browser = playwright.chromium.launch(headless=True, args=STEALTH_ARGS)
        context = _new_context(browser)
        Stealth().apply_stealth_sync(context)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=35000)
        time.sleep(1.5)
        product = parse_pdp(page.content(), url)
        return _compact_product(product) if _is_valid_product(product, "lacoste.com.br") else None
    except Exception:
        return None
    finally:
        for name in ("page", "context", "browser"):
            handle = locals().get(name)
            try:
                if handle:
                    handle.close()
            except Exception:
                pass


def collect_lacoste_products(playwright: Any, query: str) -> list[dict[str, Any]]:
    search_url = f"https://www.lacoste.com.br/search?q={quote_plus(query)}"
    search = fetch_page(playwright, search_url, f"lacoste-search-{query}-stealth", "stealth")
    products = list(search.products)
    for candidate in search.candidates:
        if len(products) >= 3:
            break
        product = fetch_product(playwright, candidate, "stealth")
        if product:
            products.append(product)
        time.sleep(1.0)
    return _dedupe_products(products)


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


def probe_zara(playwright: Any) -> tuple[list[ProbeResult], str]:
    probes = [
        fetch_page(playwright, "https://www.zara.com/br/", "zara-home-stealth", "stealth"),
        fetch_page(playwright, "https://www.zara.com/br/pt/search?searchTerm=polo", "zara-search-stealth", "stealth"),
    ]
    outcome = "DEFERIR"
    for probe in probes:
        blocked = bool(probe.blocked_signals or probe.error)
        if probe.ok and not blocked and probe.html_bytes > 5000 and ("zara" in probe.title.lower() or "zara" in probe.final_url.lower()):
            outcome = "PROMOVER_REQUISITO_FUTURO"
            break
    return probes, outcome


def choose_verdict(first_round: list[dict[str, Any]], second_round: list[dict[str, Any]]) -> str:
    if len(first_round) >= 3 and len(second_round) >= 3:
        return "GO_ACTIVATION"
    if first_round or second_round:
        return "GO_TECHNICAL"
    return "NO-GO"


def product_table(products: list[dict[str, Any]]) -> str:
    if not products:
        return "- Nenhum produto real com titulo + URL Lacoste + preco positivo.\n"
    lines = ["| Titulo | URL | Preco |", "|---|---|---|"]
    for product in products:
        title = str(product.get("title") or "").replace("|", "\\|")
        lines.append(f"| {title} | {product.get('url')} | {product.get('price')} |")
    return "\n".join(lines) + "\n"


def probe_table(probes: list[ProbeResult]) -> str:
    lines = ["| Probe | Modo | Status | Bytes | Final URL | Bloqueio | SFCC | Erro |", "|---|---|---:|---:|---|---|---|---|"]
    for probe in probes:
        block = ", ".join(probe.blocked_signals) or "-"
        sfcc = ", ".join(probe.sfcc_signals) or "-"
        error = (probe.error or "-").replace("|", "\\|")
        final_url = (probe.final_url or "-").replace("|", "\\|")
        lines.append(
            f"| {probe.label} | {probe.mode} | {probe.status or '-'} | {probe.html_bytes} | "
            f"{final_url} | {block} | {sfcc} | {error} |"
        )
    return "\n".join(lines) + "\n"


def write_report(
    probes: list[ProbeResult],
    first_query: str,
    first_round: list[dict[str, Any]],
    second_round: list[dict[str, Any]],
    zara_probes: list[ProbeResult],
    zara_outcome: str,
    verdict: str,
    exception: str = "",
) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    next_step = {
        "GO_ACTIVATION": "Executar 36-02 e 36-03; 36-03 ainda deve validar smoke via engine real antes de ativar brands.json.",
        "GO_TECHNICAL": "Executar 36-02; nao ativar Lacoste sem D-06 no smoke integrado.",
        "NO-GO": "Parar a phase, manter lacoste.is_active=false e nao executar 36-02/36-03.",
    }[verdict]
    report = f"""# Spike 008 - Lacoste anti-bot + Zara recheck

Gerado em: {generated}

## Veredito

**Lacoste:** `{verdict}`

**Zara:** `{zara_outcome}`

## Lacoste

Query usada para decisao: `{first_query}`

### Rodada 1

{product_table(first_round)}

### Rodada 2

{product_table(second_round)}

## Zara

Resultado: `{zara_outcome}`

{probe_table(zara_probes)}

Zara foi apenas reavaliada. Nenhum engine Zara foi criado e nenhum endpoint interno/mobile privado foi usado.

## Tecnicas testadas

- Baseline Playwright publico: Chromium headless, contexto desktop pt-BR e fingerprint masking basico equivalente ao BrowserManager.
- Stealth publico permitido: `playwright_stealth.Stealth().apply_stealth_sync(context)`, user-agent desktop, locale `pt-BR`, timezone `America/Sao_Paulo`, viewport 1366x768, headers Sec-CH-UA/Accept-Language coerentes.
- Baixa frequencia: probes sequenciais com sleeps curtos; sem concorrencia.

## Evidencia

### Probes Lacoste

{probe_table(probes)}

### Produtos Lacoste consolidados

{product_table(_dedupe_products(first_round + second_round))}

## Decisao do gate

{next_step}

## Proibicoes respeitadas

- Nao foi usado proxy residencial, gateway pago de scraping, CAPTCHA solving, browser headed/manual, perfil persistente real, login, credenciais privadas, OCAPI/SCAPI ou endpoint interno/mobile privado.
- O spike nao alterou `backend/` nem `backend/data/brands.json`.
"""
    if exception:
        report += f"\n## Excecao do script\n\n```text\n{exception}\n```\n"
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    probes: list[ProbeResult] = []
    first_round: list[dict[str, Any]] = []
    second_round: list[dict[str, Any]] = []
    zara_probes: list[ProbeResult] = []
    zara_outcome = "DEFERIR"
    query_used = "polo"
    verdict = "NO-GO"
    exception = ""

    try:
        with sync_playwright() as playwright:
            lacoste_urls = [
                ("lacoste-home-baseline", "https://www.lacoste.com.br/", "baseline"),
                ("lacoste-search-polo-baseline", "https://www.lacoste.com.br/search?q=polo", "baseline"),
                ("lacoste-search-camisa-baseline", "https://www.lacoste.com.br/search?q=camisa", "baseline"),
                ("lacoste-home-stealth", "https://www.lacoste.com.br/", "stealth"),
                ("lacoste-search-polo-stealth", "https://www.lacoste.com.br/search?q=polo", "stealth"),
                ("lacoste-search-camisa-stealth", "https://www.lacoste.com.br/search?q=camisa", "stealth"),
            ]
            for label, url, mode in lacoste_urls:
                probes.append(fetch_page(playwright, url, label, mode))
                time.sleep(1.0)

            for query in ("polo", "camisa"):
                first = collect_lacoste_products(playwright, query)
                time.sleep(2.0)
                second = collect_lacoste_products(playwright, query)
                if first or second:
                    query_used = query
                    first_round = first
                    second_round = second
                    break

            zara_probes, zara_outcome = probe_zara(playwright)
            verdict = choose_verdict(first_round, second_round)
    except Exception as exc:  # noqa: BLE001 - always write report
        exception = f"{type(exc).__name__}: {exc}"
    finally:
        write_report(probes, query_used, first_round, second_round, zara_probes, zara_outcome, verdict, exception)

    print(json.dumps({"lacoste_verdict": verdict, "zara_outcome": zara_outcome, "report": str(REPORT_PATH)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
