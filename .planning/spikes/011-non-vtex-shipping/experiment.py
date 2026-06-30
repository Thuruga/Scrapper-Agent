from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp


ROOT = Path(__file__).resolve().parents[3]
BRANDS_PATH = ROOT / "backend" / "data" / "brands.json"
REPORT_PATH = Path(__file__).with_name("REPORT.md")
GRAPHQL_ENDPOINT = "https://storefront-api.fbits.net/graphql"
DEFAULT_CEP = "01415000"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


@dataclass
class ProbeResult:
    provider: str
    brand_key: str
    domain: str
    product_url: str = ""
    status: str = ""
    state: str = "temporary_failure"
    options_count: int = 0
    sample_options: list[dict[str, Any]] = field(default_factory=list)
    response_signature: str = ""
    verdict: str = "NO-GO"
    notes: list[str] = field(default_factory=list)


def load_brands() -> dict[str, Any]:
    return json.loads(BRANDS_PATH.read_text(encoding="utf-8"))


def clean_cep(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 8:
        raise ValueError("CEP must have 8 digits")
    return digits


def masked_cep(value: str) -> str:
    digits = clean_cep(value)
    return f"{digits[:5]}***"


def price_to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", ".").strip()), 2)
    except (TypeError, ValueError):
        return None


def has_go_options(options: list[dict[str, Any]]) -> bool:
    for opt in options:
        has_price = opt.get("price") is not None
        has_delivery_text = bool(
            opt.get("deadline")
            or opt.get("deadlineInHours")
            or opt.get("delivery_date")
            or opt.get("delivery_days")
            or opt.get("estimate")
        )
        if has_price and has_delivery_text:
            return True
    return False


async def fetch_json(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    *,
    timeout: float,
    **kwargs: Any,
) -> tuple[int, Any, str]:
    async with session.request(
        method,
        url,
        timeout=aiohttp.ClientTimeout(total=timeout),
        **kwargs,
    ) as resp:
        text = await resp.text()
        try:
            data = json.loads(text) if text else None
        except json.JSONDecodeError:
            data = text[:500]
        return resp.status, data, resp.content_type


async def discover_shopify_product(
    session: aiohttp.ClientSession, domain: str, timeout: float
) -> tuple[dict[str, Any], dict[str, Any], str]:
    status, data, _ = await fetch_json(
        session,
        "GET",
        f"https://{domain}/products.json?limit=20",
        timeout=timeout,
    )
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"products.json returned HTTP {status}")

    for product in data.get("products") or []:
        variants = product.get("variants") or []
        variant = next((v for v in variants if v.get("available", True)), None)
        if product.get("handle") and variant and variant.get("id"):
            product_url = f"https://{domain}/products/{product['handle']}"
            return product, variant, product_url
    raise RuntimeError("no available Shopify product/variant found")


async def shopify_quote_once(
    domain: str,
    variant_id: int | str,
    cep: str,
    timeout: float,
) -> tuple[int, list[dict[str, Any]], str]:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        await fetch_json(session, "POST", f"https://{domain}/cart/clear.js", timeout=timeout, json={})
        add_status, _, _ = await fetch_json(
            session,
            "POST",
            f"https://{domain}/cart/add.js",
            timeout=timeout,
            json={"id": variant_id, "quantity": 1},
        )
        if add_status >= 400:
            return add_status, [], "cart/add.js failed"

        params = {
            "shipping_address[zip]": cep,
            "shipping_address[country]": "Brazil",
            "shipping_address[country_code]": "BR",
            "shipping_address[province]": "SP",
            "shipping_address[city]": "Sao Paulo",
        }
        prepare_status, _, _ = await fetch_json(
            session,
            "POST",
            f"https://{domain}/cart/prepare_shipping_rates.json",
            timeout=timeout,
            params=params,
        )
        if prepare_status not in (200, 202):
            return prepare_status, [], "prepare_shipping_rates failed"

        last_status = prepare_status
        last_signature = "async_shipping_rates pending"
        for _ in range(5):
            await asyncio.sleep(1)
            last_status, data, _ = await fetch_json(
                session,
                "GET",
                f"https://{domain}/cart/async_shipping_rates.json",
                timeout=timeout,
                params=params,
            )
            if isinstance(data, dict) and data.get("shipping_rates") is not None:
                rates = data.get("shipping_rates") or []
                options = []
                for rate in rates:
                    price = price_to_float(rate.get("price"))
                    options.append(
                        {
                            "name": rate.get("presentment_name") or rate.get("name"),
                            "price": price,
                            "delivery_date": rate.get("delivery_date"),
                            "delivery_days": rate.get("delivery_days"),
                            "source": rate.get("source"),
                        }
                    )
                await fetch_json(
                    session,
                    "POST",
                    f"https://{domain}/cart/clear.js",
                    timeout=timeout,
                    json={},
                )
                return last_status, options, "shipping_rates[] returned"
            last_signature = f"async status={last_status}"

        await fetch_json(session, "POST", f"https://{domain}/cart/clear.js", timeout=timeout, json={})
        return last_status, [], last_signature


async def probe_shopify(cep: str, timeout: float) -> ProbeResult:
    brands = load_brands()
    brand = brands["bck"]
    domain = brand["domain"]
    result = ProbeResult(
        provider="Shopify/Buckman",
        brand_key="bck",
        domain=domain,
        notes=["Primary Shopify target is Buckman/BCK; roadmap VTEX mention is ignored."],
    )

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            product, variant, product_url = await discover_shopify_product(session, domain, timeout)
        result.product_url = product_url
        result.notes.append(f"Product: {product.get('title')} / variant_id={variant.get('id')}")

        runs = []
        for _ in range(2):
            status, options, signature = await shopify_quote_once(
                domain, variant["id"], cep, timeout
            )
            runs.append((status, options, signature))

        result.status = ",".join(str(status) for status, _, _ in runs)
        result.sample_options = runs[-1][1]
        result.options_count = len(result.sample_options)
        result.response_signature = runs[-1][2]

        if all(status == 200 for status, _, _ in runs) and all(
            has_go_options(options) for _, options, _ in runs
        ):
            result.state = "available"
            result.verdict = "GO"
        else:
            result.verdict = "NO-GO"
            result.notes.append("No repeated quote with price and delivery text/date.")
    except Exception as exc:
        result.response_signature = f"{type(exc).__name__}: {exc}"
        result.notes.append("Exception during Shopify probe.")

    return result


WAKE_PRODUCT_QUERY = """
query WakeSearch($q: String!, $first: Int!) {
  search(query: $q) {
    products(first: $first) {
      edges {
        node {
          productName
          aliasComplete
          available
          productId
          productVariantId
          sku
          prices { price }
        }
      }
    }
  }
}
""".strip()


WAKE_SHIPPING_QUERY = """
query Shipping($cep: CEP, $productVariantId: Long, $quantity: Int) {
  shippingQuotes(
    cep: $cep,
    productVariantId: $productVariantId,
    quantity: $quantity
  ) {
    shippingQuoteId
    name
    value
    deadline
    deadlineInHours
    type
    distributionCenterId
  }
}
""".strip()


async def wake_graphql(
    session: aiohttp.ClientSession,
    token: str,
    query: str,
    variables: dict[str, Any],
    timeout: float,
) -> tuple[int, dict[str, Any] | None]:
    status, data, _ = await fetch_json(
        session,
        "POST",
        GRAPHQL_ENDPOINT,
        timeout=timeout,
        json={"query": query, "variables": variables},
        headers={"TCS-Access-Token": token, "Accept": "application/json"},
    )
    return status, data if isinstance(data, dict) else None


async def probe_wake(cep: str, timeout: float) -> ProbeResult:
    brands = load_brands()
    brand = brands["richards"]
    domain = brand["domain"]
    token = brand.get("wake_access_token") or ""
    result = ProbeResult(
        provider="Wake/Richards",
        brand_key="richards",
        domain=domain,
        notes=["Uses public Storefront GraphQL token already stored for Richards."],
    )

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            status, data = await wake_graphql(
                session, token, WAKE_PRODUCT_QUERY, {"q": "camisa", "first": 1}, timeout
            )
            if status != 200 or not data or data.get("errors"):
                result.status = str(status)
                result.response_signature = json.dumps(data or {})[:500]
                result.verdict = "NO-GO"
                return result

            edge = (
                (data.get("data") or {})
                .get("search", {})
                .get("products", {})
                .get("edges", [{}])[0]
            )
            node = edge.get("node") or {}
            variant_id = node.get("productVariantId")
            alias = node.get("aliasComplete") or ""
            if not variant_id:
                result.status = "200"
                result.response_signature = "productVariantId missing"
                result.verdict = "NO-GO"
                return result

            result.product_url = f"https://{domain}/{alias.lstrip('/')}" if alias else ""
            result.notes.append(
                f"Product: {node.get('productName')} / productVariantId={variant_id} / sku={node.get('sku')}"
            )

            runs = []
            for _ in range(2):
                status, quote_data = await wake_graphql(
                    session,
                    token,
                    WAKE_SHIPPING_QUERY,
                    {"cep": cep, "productVariantId": int(variant_id), "quantity": 1},
                    timeout,
                )
                quotes = []
                if quote_data and not quote_data.get("errors"):
                    for quote in ((quote_data.get("data") or {}).get("shippingQuotes") or []):
                        quotes.append(
                            {
                                "name": quote.get("name"),
                                "price": price_to_float(quote.get("value")),
                                "deadline": quote.get("deadline"),
                                "deadlineInHours": quote.get("deadlineInHours"),
                                "type": quote.get("type"),
                            }
                        )
                signature = "shippingQuotes[] returned" if quotes else json.dumps(quote_data or {})[:500]
                runs.append((status, quotes, signature))

        result.status = ",".join(str(status) for status, _, _ in runs)
        result.sample_options = runs[-1][1]
        result.options_count = len(result.sample_options)
        result.response_signature = runs[-1][2]
        if all(status == 200 for status, _, _ in runs) and all(
            has_go_options(options) for _, options, _ in runs
        ):
            result.state = "available"
            result.verdict = "GO"
        else:
            result.verdict = "NO-GO"
            result.notes.append("No repeated quote with price and delivery deadline.")
    except Exception as exc:
        result.response_signature = f"{type(exc).__name__}: {exc}"
        result.notes.append("Exception during Wake probe.")

    return result


def render_report(results: list[ProbeResult], cep: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Spike 011: Non-VTEX Shipping",
        "",
        f"Generated: {generated}",
        f"CEP used: {masked_cep(cep)}",
        "",
        "## Verdict",
        "",
        "| Provider | Brand | Verdict | State | Options | Status |",
        "|----------|-------|---------|-------|---------|--------|",
    ]
    for r in results:
        lines.append(
            f"| {r.provider} | {r.brand_key} | {r.verdict} | {r.state} | {r.options_count} | {r.status or '-'} |"
        )
    lines.extend(["", "## Evidence", ""])
    for r in results:
        lines.extend(
            [
                f"### {r.provider}",
                "",
                f"- Brand key: `{r.brand_key}`",
                f"- Domain: `{r.domain}`",
                f"- Product URL: `{r.product_url or 'n/a'}`",
                f"- Response signature: `{r.response_signature or 'n/a'}`",
                f"- Options count: {r.options_count}",
                "- Sample options:",
            ]
        )
        if r.sample_options:
            for opt in r.sample_options[:5]:
                lines.append(f"  - `{json.dumps(opt, ensure_ascii=True)}`")
        else:
            lines.append("  - none")
        lines.append("- Notes:")
        for note in r.notes:
            lines.append(f"  - {note}")
        lines.append("")

    lines.extend(
        [
            "## Implementation Decisions",
            "",
            "- Shopify/Buckman: implement real provider using Shopify Ajax Cart (`cart/add.js`, `prepare_shipping_rates.json`, `async_shipping_rates.json`) when verdict is GO.",
            "- Wake/Richards: implement real provider using Storefront GraphQL `shippingQuotes(cep, productVariantId, quantity)` when verdict is GO.",
            "- VTEX remains unchanged in `VtexApiClient`; do not route VTEX through `BaseShipping`.",
            "- SFCC remains unsupported in Phase 41.",
            "",
        ]
    )
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["all", "shopify", "wake"], default="all")
    parser.add_argument("--cep", default=DEFAULT_CEP)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    cep = clean_cep(args.cep)
    results: list[ProbeResult] = []
    if args.provider in ("all", "shopify"):
        results.append(await probe_shopify(cep, args.timeout))
    if args.provider in ("all", "wake"):
        results.append(await probe_wake(cep, args.timeout))

    report = render_report(results, cep)
    if args.write_report:
        REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)

    return 0 if all(r.verdict == "GO" for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
