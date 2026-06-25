"""
Spike 009 - probe_search: descobre empiricamente a URL de busca/catalogo da Lacoste
que retorna GRADE DE PRODUTOS, testando candidatos no host canonico www.lacoste.com/br/.

A busca anterior (lacoste.com.br/search?q=polo) redirecionou pra home e nao tinha produto.
Aqui testamos varios padroes SFCC + uma categoria conhecida (masculino.html) como controle.
Reaproveita o perfil persistente quente. Nao altera backend/.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

SPIKE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = SPIKE_DIR / "chrome-profile"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

CANDIDATES = [
    ("search_seo_canonical", "https://www.lacoste.com/br/search?q=polo"),
    ("search_q_lower", "https://www.lacoste.com/br/?q=polo"),
    ("search_ctrl_show", "https://www.lacoste.com/on/demandware.store/Sites-BRECOM-Site/pt_BR/Search-Show?q=polo"),
    ("category_masculino", "https://www.lacoste.com/br/masculino.html"),
    ("category_polos", "https://www.lacoste.com/br/masculino/roupas/polos.html"),
]


def signals_for(html: str, final_url: str, title: str) -> dict:
    low = html.lower()
    soup = BeautifulSoup(html, "html.parser")
    pids = [el.get("data-pid") for el in soup.select("[data-pid]")][:8]
    return {
        "final_url": final_url,
        "title": title,
        "bytes": len(html.encode("utf-8")),
        "data_pid": low.count("data-pid"),
        "product_tile": low.count("product-tile"),
        "price_rs": len(re.findall(r"r\$\s*\d", low)),
        "pid_samples": [p for p in pids if p],
    }


def main() -> int:
    out = []
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
        except Exception:
            pass
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        for label, url in CANDIDATES:
            print(f"\n-> [{label}] {url}")
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_selector("[data-pid], .product-tile", timeout=7000)
                except Exception:
                    pass
                try:
                    page.mouse.wheel(0, 4000)
                    page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                html = page.content()
                sig = signals_for(html, page.url, page.title())
                sig["label"] = label
                sig["status"] = resp.status if resp else None
                out.append(sig)
                print(json.dumps(sig, ensure_ascii=False))
                # salva o html do candidato mais promissor (com data-pid)
                if sig["data_pid"] > 0:
                    (SPIKE_DIR / f"{label}.html").write_text(html, encoding="utf-8")
                    print(f"   ^ produtos detectados — HTML salvo em {label}.html")
            except Exception as exc:  # noqa: BLE001
                print(f"   erro: {type(exc).__name__}: {exc}")
            page.wait_for_timeout(1500)

        ctx.close()

    print("\n=== RESUMO ===")
    for sig in sorted(out, key=lambda s: s.get("data_pid", 0), reverse=True):
        print(f"{sig['label']:24} status={sig.get('status')} data_pid={sig['data_pid']:4} "
              f"tiles={sig['product_tile']:4} R$={sig['price_rs']:3} -> {sig['final_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
