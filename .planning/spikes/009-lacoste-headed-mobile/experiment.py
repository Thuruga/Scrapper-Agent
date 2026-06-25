"""
Spike 009 - Lacoste anti-bot: navegador HEADED + perfil persistente, via REDE MOVEL.

Contexto: o spike 008 deu NO-GO para a Lacoste com Chromium HEADLESS rodando da
rede corporativa da Aramis. Toda tentativa tomou 403 / Access Denied / akamai_reference.
Como o disfarce de navegador (stealth) nao mudou nada entre baseline e stealth, a
hipotese e que o bloqueio do Akamai e por REPUTACAO DE IP/REDE, nao por fingerprint.

Este spike testa as UNICAS alavancas GRATIS que sobraram (autorizadas pelo usuario):
  1) navegador HEADED (janela visivel) em vez de headless;
  2) PERFIL PERSISTENTE (cookies/sessao reaproveitados, sessao unica e "quente");
  3) rodar de uma REDE DIFERENTE — dados moveis (4G/5G) do celular, IP "limpo".

NAO usa: proxy residencial pago, gateway de scraping pago, CAPTCHA solving, login,
credenciais privadas, OCAPI/SCAPI nem endpoint interno/mobile privado.
NAO altera backend/ nem backend/data/brands.json.

Como rodar:
  1. Conecte o PC ao roteamento de dados moveis do celular (4G/5G).
  2. Confirme que saiu da rede da Aramis (veja o IP publico que o script imprime).
  3. python .planning/spikes/009-lacoste-headed-mobile/experiment.py
  4. Observe a janela do Chrome. Para cada pagina, espere carregar e aperte ENTER
     para capturar (modo --no-pause captura sozinho sem esperar).
  5. O script escreve REPORT.md e imprime o veredito.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from services.engines.sfcc_parser import parse_pdp, parse_search_results  # noqa: E402

SPIKE_DIR = Path(__file__).resolve().parent
REPORT_PATH = SPIKE_DIR / "REPORT.md"
PROFILE_DIR = SPIKE_DIR / "chrome-profile"  # perfil persistente (cookies/sessao)

# Args minimos: nada que grite "automacao". A flag AutomationControlled e a unica
# mascara relevante; o resto fica no default do Chrome real para parecer humano.
CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--start-maximized",
]
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
DOMAIN = "lacoste.com.br"


@dataclass
class ProbeResult:
    label: str
    url: str
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


def _is_valid_product(product: Optional[dict[str, Any]]) -> bool:
    if not product:
        return False
    url = str(product.get("url") or "")
    return bool(
        product.get("raw_title")
        and DOMAIN in url
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


def _maybe_pause(label: str, pause: bool) -> None:
    if not pause:
        return
    try:
        input(f"  [{label}] Veja a janela do Chrome. Apos carregar (ou interagir), aperte ENTER para capturar...")
    except EOFError:
        pass


def probe(page: Any, label: str, url: str, pause: bool, timeout_ms: int = 45000) -> ProbeResult:
    """Navega na MESMA pagina/sessao quente e analisa o resultado."""
    result = ProbeResult(label=label, url=url)
    print(f"\n-> [{label}] {url}")
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # Deixa o sensor JS do Akamai rodar e a pagina hidratar.
        page.wait_for_timeout(5000)
        _maybe_pause(label, pause)
        html = page.content()
        result.ok = True
        result.status = response.status if response else None
        result.final_url = page.url
        try:
            result.title = page.title()
        except Exception:
            result.title = ""
        result.html_bytes = len(html.encode("utf-8"))
        result.blocked_signals = _detect_block(html, result.status)
        result.sfcc_signals = _detect_sfcc(html)
        if "search" in url:
            result.candidates = parse_search_results(html, DOMAIN)[:3]
        else:
            parsed = parse_pdp(html, f"https://www.{DOMAIN}/")
            if _is_valid_product(parsed):
                result.products = [_compact_product(parsed)]
    except PlaywrightTimeoutError as exc:
        result.error = f"timeout: {exc}"
    except Exception as exc:  # noqa: BLE001 - spike registra falha, nao quebra
        result.error = f"{type(exc).__name__}: {exc}"
    print(
        f"   status={result.status} bytes={result.html_bytes} "
        f"block={result.blocked_signals or '-'} sfcc={result.sfcc_signals or '-'} "
        f"candidates={len(result.candidates)} products={len(result.products)} err={result.error or '-'}"
    )
    return result


def collect_products(page: Any, query: str, pause: bool) -> tuple[ProbeResult, list[dict[str, Any]]]:
    """Busca por `query` na sessao quente e tenta extrair ate 3 produtos reais."""
    search_url = f"https://www.{DOMAIN}/search?q={quote_plus(query)}"
    search = probe(page, f"lacoste-search-{query}-headed", search_url, pause)
    products = list(search.products)
    for candidate in search.candidates:
        if len(products) >= 3:
            break
        # probe() ja roda parse_pdp e popula .products quando a PDP e valida.
        pdp = probe(page, f"lacoste-pdp-{query}", candidate, pause=False)
        products.extend(pdp.products)
        time.sleep(1.5)
    return search, _dedupe_products(products)


def choose_verdict(products: list[dict[str, Any]], any_search_200: bool) -> str:
    if len(products) >= 3:
        return "GO_ACTIVATION"
    if products:
        return "GO_TECHNICAL"
    if any_search_200:
        return "PARCIAL_PAGINA_CARREGOU_SEM_PRODUTO"
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
    lines = [
        "| Probe | Status | Bytes | Final URL | Bloqueio | SFCC | Cand. | Prod. | Erro |",
        "|---|---:|---:|---|---|---|---:|---:|---|",
    ]
    for p in probes:
        block = ", ".join(p.blocked_signals) or "-"
        sfcc = ", ".join(p.sfcc_signals) or "-"
        error = (p.error or "-").replace("|", "\\|")
        final_url = (p.final_url or "-").replace("|", "\\|")
        lines.append(
            f"| {p.label} | {p.status or '-'} | {p.html_bytes} | {final_url} | "
            f"{block} | {sfcc} | {len(p.candidates)} | {len(p.products)} | {error} |"
        )
    return "\n".join(lines) + "\n"


def public_ip() -> str:
    """Imprime o IP publico para o usuario confirmar que saiu da rede da Aramis."""
    try:
        import urllib.request

        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception as exc:  # noqa: BLE001
        return f"(nao foi possivel obter: {type(exc).__name__})"


def write_report(ip: str, probes: list[ProbeResult], products: list[dict[str, Any]], verdict: str, exception: str = "") -> None:
    generated = datetime.now(timezone.utc).isoformat()
    next_step = {
        "GO_ACTIVATION": "Caminho gratis VIAVEL via headed+perfil+rede movel. Planejar engine/fetcher dedicado e validar repetibilidade antes de ativar brands.json.",
        "GO_TECHNICAL": "Rota tecnica provada (>=1 produto), mas abaixo de D-06. Repetir e investigar estabilidade antes de ativar.",
        "PARCIAL_PAGINA_CARREGOU_SEM_PRODUTO": "A pagina carregou (sem 403), mas o parser nao extraiu produto. Provavel ajuste de parser/seletor OU render assincrono. Vale uma segunda iteracao do parser, nao desistir ainda.",
        "NO-GO": "Mesmo headed + perfil persistente + rede movel falharam. Conclusao honesta: Lacoste fica adiada ate haver verba para proxy/gateway. Manter is_active=false.",
    }[verdict]
    report = f"""# Spike 009 - Lacoste headed + perfil persistente via rede movel

Gerado em: {generated}

IP publico de origem (deve ser do celular/4G, nao da Aramis): `{ip}`

## Veredito

**Lacoste:** `{verdict}`

## Tecnica testada (alavancas gratis)

- Navegador HEADED (janela visivel), nao headless.
- Perfil PERSISTENTE (`launch_persistent_context`) — sessao unica e quente: home primeiro, depois buscas, reaproveitando cookies (`_abck` etc.).
- `playwright_stealth` aplicado, UA/locale `pt-BR`/timezone `America/Sao_Paulo`/headers coerentes.
- Origem: rede de dados moveis (4G/5G), IP fora da rede corporativa.
- Baixa frequencia, sequencial, sem concorrencia.

## Evidencia

{probe_table(probes)}

### Produtos consolidados

{product_table(products)}

## Decisao do gate

{next_step}

## Proibicoes respeitadas

- HEADED + perfil persistente foram USADOS (autorizados pelo usuario nesta tentativa gratis).
- NAO foi usado: proxy residencial pago, gateway de scraping pago, CAPTCHA solving, login,
  credenciais privadas, OCAPI/SCAPI nem endpoint interno/mobile privado.
- O spike NAO alterou `backend/` nem `backend/data/brands.json`.
"""
    if exception:
        report += f"\n## Excecao do script\n\n```text\n{exception}\n```\n"
    REPORT_PATH.write_text(report, encoding="utf-8")


def main() -> int:
    pause = "--no-pause" not in sys.argv and os.environ.get("SPIKE_NO_PAUSE") != "1"
    probes: list[ProbeResult] = []
    products: list[dict[str, Any]] = []
    verdict = "NO-GO"
    exception = ""
    any_search_200 = False

    ip = public_ip()
    print("=" * 64)
    print(f"IP publico de origem: {ip}")
    print("  -> confirme que NAO e o IP da rede da Aramis (deve ser do 4G/celular).")
    print(f"  -> modo: {'INTERATIVO (espera ENTER)' if pause else 'AUTOMATICO (--no-pause)'}")
    print("=" * 64)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                headless=False,
                args=CHROMIUM_ARGS,
                user_agent=USER_AGENT,
                locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                viewport={"width": 1366, "height": 768},
                extra_http_headers=HEADERS,
            )
            try:
                Stealth().apply_stealth_sync(context)
            except Exception as exc:  # noqa: BLE001
                print(f"  (stealth nao aplicou, seguindo: {exc})")

            page = context.pages[0] if context.pages else context.new_page()

            # 1) Esquenta a sessao na home (deixa o Akamai setar cookie de sessao).
            home = probe(page, "lacoste-home-headed", f"https://www.{DOMAIN}/", pause)
            probes.append(home)
            time.sleep(2.0)

            # 2) Busca por polo (e camisa como fallback), na mesma sessao quente.
            for query in ("polo", "camisa"):
                search, found = collect_products(page, query, pause)
                probes.append(search)
                if search.status == 200 and not search.blocked_signals:
                    any_search_200 = True
                if found:
                    products = found
                    break
                time.sleep(2.0)

            verdict = choose_verdict(products, any_search_200)
    except Exception as exc:  # noqa: BLE001 - sempre escreve report
        exception = f"{type(exc).__name__}: {exc}"
    finally:
        write_report(ip, probes, products, verdict, exception)

    print("\n" + "=" * 64)
    print(json.dumps({"lacoste_verdict": verdict, "origin_ip": ip, "report": str(REPORT_PATH)}, ensure_ascii=False))
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
