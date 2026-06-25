"""
Spike 009 - inspect: captura o HTML real da busca da Lacoste (do 4G) e mede a
estrutura, para decidir se os produtos estao no HTML (fix de parser) ou se sao
renderizados de forma assincrona (precisa esperar a grade / bater na API SFCC).

Reaproveita o perfil persistente ja "quente" do experiment.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

SPIKE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = SPIKE_DIR / "chrome-profile"
OUT_HTML = SPIKE_DIR / "search_polo.html"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
URL = "https://www.lacoste.com.br/search?q=polo"

# Seletores tipicos de grade de produto em SFCC/Demandware (e genericos).
PRODUCT_SELECTORS = [
    "[data-pid]",
    ".product-tile",
    ".product-grid",
    ".product-grid__item",
    "[itemtype*='Product']",
    "div.product",
    "a[href*='.html']",
]


def main() -> int:
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            user_agent=UA,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
        )
        try:
            Stealth().apply_stealth_sync(ctx)
        except Exception as exc:  # noqa: BLE001
            print(f"(stealth nao aplicou: {exc})")

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        resp = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        print(f"goto status={resp.status if resp else '-'} final_url={page.url}")

        # Tenta esperar a grade de produtos renderizar (sinal de render assincrono).
        appeared = None
        for sel in PRODUCT_SELECTORS:
            try:
                page.wait_for_selector(sel, timeout=6000)
                appeared = sel
                print(f"selector apareceu (render OK): {sel}")
                break
            except Exception:
                pass
        if not appeared:
            print("nenhum seletor de produto apareceu em ~6s/seletor")

        # Tenta rolar a pagina pra disparar lazy-load e espera a rede assentar.
        try:
            page.mouse.wheel(0, 4000)
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        html = page.content()
        OUT_HTML.write_text(html, encoding="utf-8")
        low = html.lower()

        signals = {
            "bytes": len(html.encode("utf-8")),
            "final_url": page.url,
            "title": page.title(),
            "selector_appeared": appeared or "(nenhum)",
            "count_data_pid": low.count("data-pid"),
            "count_product_tile": low.count("product-tile"),
            "count_product_grid": low.count("product-grid"),
            "count_jsonld_product": low.count('"@type":"product"') + low.count('"@type": "product"'),
            "count_price_rs": len(re.findall(r"r\$\s*\d", low)),
            "count_href_html": len(re.findall(r'href="[^"]*\.html', low)),
            "has_state_blob": any(k in low for k in ["__next_data__", "window.__", "__preloaded", "digitaldata"]),
        }
        print("\n=== SINAIS DE ESTRUTURA ===")
        print(json.dumps(signals, ensure_ascii=False, indent=2))

        soup = BeautifulSoup(html, "html.parser")
        pid_els = soup.select("[data-pid]")[:6]
        print("\ndata-pid samples:", [el.get("data-pid") for el in pid_els])
        html_links = []
        for a in soup.find_all("a", href=True):
            if ".html" in a["href"]:
                html_links.append(a["href"])
            if len(html_links) >= 8:
                break
        print("sample .html links:", html_links)

        ctx.close()

    print(f"\nHTML salvo em: {OUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
