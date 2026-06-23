"""
Standalone MVP probe for SFCC / Inditex public storefront feasibility.

This script intentionally does not import the app's production services or engines.
It only requests robots.txt and a public homepage for each target, then writes a
local report. It does not retry aggressively, bypass bot protection, solve
challenges, or call checkout/account/internal API routes.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple


SPIKE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(SPIKE_DIR, "REPORT.md")
JSON_PATH = os.path.join(SPIKE_DIR, "report.json")

USER_AGENT = "e-scraper-public-storefront-research/0.1"
TIMEOUT_SECONDS = 12
MAX_BODY_CHARS = 350_000


TARGETS = [
    {
        "key": "hugoboss_us",
        "name": "Hugo Boss US",
        "expected_path": "sfcc",
        "base_url": "https://www.hugoboss.com/us/",
    },
    {
        "key": "lacoste_us",
        "name": "Lacoste US",
        "expected_path": "sfcc",
        "base_url": "https://www.lacoste.com/us/",
    },
    {
        "key": "zara_br",
        "name": "Zara BR",
        "expected_path": "inditex",
        "base_url": "https://www.zara.com/br/",
    },
]


SENSITIVE_PATTERNS = [
    "cart",
    "checkout",
    "account",
    "wishlist",
    "availability",
    "retailavailability",
    "payment",
    "login",
    "users",
    "mini-shop-cart",
    "guest-user",
    "akam",
    "botfende",
]


SFCC_SIGNALS = [
    "demandware",
    "dwcont",
    "dwanonymous",
    "salesforcetracking",
    "product-show",
    "search-show",
    "cgid=",
    "sfra",
]


INDITEX_SIGNALS = [
    "inditex",
    "itxsessionid",
    "zara.com",
    "zara",
    "iop",
]


@dataclass
class FetchResult:
    url: str
    status: int | None
    ok: bool
    error: str | None
    body: str
    elapsed_ms: int


@dataclass
class TargetReport:
    key: str
    name: str
    expected_path: str
    robots_url: str
    homepage_url: str
    robots_status: int | None
    homepage_status: int | None
    robots_error: str | None
    homepage_error: str | None
    sitemaps: List[str]
    disallow_count: int
    sensitive_disallow_hits: List[str]
    platform_signals: Dict[str, int]
    product_link_hints: int
    category_link_hints: int
    classification: str
    recommendation: str


def fetch_url(url: str) -> FetchResult:
    start = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read(MAX_BODY_CHARS)
            body = raw.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
            return FetchResult(
                url=url,
                status=resp.status,
                ok=200 <= resp.status < 300,
                error=None,
                body=body,
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read(MAX_BODY_CHARS)
            body = raw.decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return FetchResult(
            url=url,
            status=exc.code,
            ok=False,
            error=f"HTTPError: {exc.code}",
            body=body,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )
    except Exception as exc:
        return FetchResult(
            url=url,
            status=None,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            body="",
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )


def origin_for(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_robots(body: str) -> Tuple[List[str], List[str]]:
    sitemaps: List[str] = []
    disallows: List[str] = []

    for raw_line in body.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "sitemap" and value:
            sitemaps.append(value)
        elif key == "disallow" and value:
            disallows.append(value)

    return sitemaps, disallows


def count_signals(text: str, signals: List[str]) -> Dict[str, int]:
    lowered = text.lower()
    return {signal: lowered.count(signal) for signal in signals if lowered.count(signal) > 0}


def extract_links(html: str, base_url: str) -> List[str]:
    links = []
    for match in re.finditer(r"""href=["']([^"']+)["']""", html, flags=re.IGNORECASE):
        href = match.group(1).strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        links.append(urllib.parse.urljoin(base_url, href))
    return links


def classify(expected_path: str, robots: FetchResult, homepage: FetchResult, signals: Dict[str, int]) -> str:
    if robots.status in {401, 403} and homepage.status in {401, 403, None}:
        return "blocked_from_local_runtime"

    if expected_path == "sfcc":
        sfcc_score = sum(signals.get(signal, 0) for signal in SFCC_SIGNALS)
        if sfcc_score > 0:
            return "sfcc_public_storefront_candidate"

    if expected_path == "inditex":
        inditex_score = sum(signals.get(signal, 0) for signal in INDITEX_SIGNALS)
        if inditex_score > 0:
            return "inditex_public_storefront_candidate"

    if homepage.status in {401, 403} or robots.status in {401, 403}:
        return "blocked_from_local_runtime"

    return "unknown_or_insufficient_signal"


def recommendation_for(classification: str, expected_path: str, sensitive_hits: List[str]) -> str:
    if classification == "blocked_from_local_runtime":
        return "stop: local runtime is blocked; do not add bypass logic"
    if expected_path == "inditex":
        return "continue-limited: product-url/public-page probe only; avoid shop/internal endpoints"
    if classification == "sfcc_public_storefront_candidate":
        return "continue: test public HTML/JSON-LD product extraction next"
    if sensitive_hits:
        return "continue-limited: public pages only; sensitive paths must stay out of scope"
    return "stop: insufficient public signal"


def probe_target(target: Dict[str, str]) -> TargetReport:
    base_url = target["base_url"]
    robots_url = urllib.parse.urljoin(origin_for(base_url), "/robots.txt")

    robots = fetch_url(robots_url)
    time.sleep(0.75)
    homepage = fetch_url(base_url)

    sitemaps, disallows = parse_robots(robots.body if robots.body else "")
    sensitive_hits = sorted(
        {
            pattern
            for pattern in SENSITIVE_PATTERNS
            for disallow in disallows
            if pattern in disallow.lower()
        }
    )

    combined_text = "\n".join([robots.body or "", homepage.body or ""])
    signals = {}
    signals.update(count_signals(combined_text, SFCC_SIGNALS))
    signals.update(count_signals(combined_text, INDITEX_SIGNALS))

    links = extract_links(homepage.body or "", base_url)
    product_hints = sum(1 for link in links if re.search(r"(-p[0-9a-z]|/p/|pid=|product-show)", link, re.I))
    category_hints = sum(1 for link in links if re.search(r"(cgid=|/c/|/category/|/men|/women|/kids)", link, re.I))

    classification = classify(target["expected_path"], robots, homepage, signals)
    recommendation = recommendation_for(classification, target["expected_path"], sensitive_hits)

    return TargetReport(
        key=target["key"],
        name=target["name"],
        expected_path=target["expected_path"],
        robots_url=robots_url,
        homepage_url=base_url,
        robots_status=robots.status,
        homepage_status=homepage.status,
        robots_error=robots.error,
        homepage_error=homepage.error,
        sitemaps=sitemaps[:20],
        disallow_count=len(disallows),
        sensitive_disallow_hits=sensitive_hits,
        platform_signals=signals,
        product_link_hints=product_hints,
        category_link_hints=category_hints,
        classification=classification,
        recommendation=recommendation,
    )


def render_markdown(reports: List[TargetReport]) -> str:
    lines = [
        "# Spike 003 Report: SFCC / Inditex Storefront MVP",
        "",
        "Generated by `experiment.py`.",
        "",
        "## Guardrails",
        "- Public homepage and robots.txt only.",
        "- No production imports.",
        "- No checkout, cart, account, wishlist, availability, or credentialed API routes.",
        "- 403/401/challenge responses are treated as stop signs.",
        "",
        "## Summary",
        "",
        "| Target | Expected | Robots | Home | Classification | Recommendation |",
        "|---|---:|---:|---:|---|---|",
    ]

    for report in reports:
        lines.append(
            "| {name} | {expected} | {robots} | {home} | {classification} | {recommendation} |".format(
                name=report.name,
                expected=report.expected_path,
                robots=report.robots_status or "-",
                home=report.homepage_status or "-",
                classification=report.classification,
                recommendation=report.recommendation,
            )
        )

    lines.extend(["", "## Details", ""])

    for report in reports:
        lines.extend(
            [
                f"### {report.name}",
                f"- Homepage: `{report.homepage_url}`",
                f"- Robots: `{report.robots_url}`",
                f"- Robots status: `{report.robots_status}` ({report.robots_error or 'ok'})",
                f"- Homepage status: `{report.homepage_status}` ({report.homepage_error or 'ok'})",
                f"- Declared sitemaps captured: `{len(report.sitemaps)}`",
                f"- Disallow rules counted: `{report.disallow_count}`",
                f"- Sensitive disallow hits: `{', '.join(report.sensitive_disallow_hits) if report.sensitive_disallow_hits else 'none'}`",
                f"- Platform signals: `{json.dumps(report.platform_signals, sort_keys=True)}`",
                f"- Product link hints on homepage: `{report.product_link_hints}`",
                f"- Category link hints on homepage: `{report.category_link_hints}`",
                f"- Classification: `{report.classification}`",
                f"- Recommendation: `{report.recommendation}`",
                "",
            ]
        )

        if report.sitemaps:
            lines.append("Sitemaps observed:")
            for sitemap in report.sitemaps[:10]:
                lines.append(f"- `{sitemap}`")
            lines.append("")

    lines.extend(
        [
            "## Next Decision",
            "If SFCC targets produce public product/category signals, the next isolated test should download a small set of public product pages from sitemap or navigation and evaluate JSON-LD/meta extraction.",
            "",
            "If Inditex remains blocked or requires `/shop/` or internal endpoints, keep it out of production integration and limit future work to authorized access or manual public product URL monitoring.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    reports = [probe_target(target) for target in TARGETS]

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(report) for report in reports], f, indent=2, ensure_ascii=False)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(render_markdown(reports))

    for report in reports:
        print(f"{report.name}: {report.classification} -> {report.recommendation}")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {JSON_PATH}")


if __name__ == "__main__":
    main()
