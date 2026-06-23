"""Production Playwright collector promoted from ``testes/extrair_banners.py``."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urljoin, urlparse

from core.banner_models import BannerCandidate, BannerVideoSlide, StoredBannerAsset
from services.banner_storage_service import BannerStorageService, banner_storage_service, friendly_banner_filename


VIEWPORT = {"width": 1366, "height": 768}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
MAX_SLIDES = 12
NAVIGATION_TIMEOUT_MS = 30_000
SETTLE_MS = 4_000
KNOWN_IMAGE_MIME = {
    "image/avif", "image/gif", "image/jpeg", "image/png", "image/svg+xml", "image/webp",
}
MIME_BY_SUFFIX = {
    ".avif": "image/avif", ".gif": "image/gif", ".jpeg": "image/jpeg", ".jpg": "image/jpeg",
    ".png": "image/png", ".svg": "image/svg+xml", ".webp": "image/webp",
}


COLLECT_BANNERS_JS = r"""
() => {
  const vw = innerWidth, vh = innerHeight;
  const absolute = (v) => { try { return (!v || /^(data:|blob:)/.test(v)) ? '' : new URL(v, location.href).href } catch { return '' } };
  const largest = (v) => (v || '').split(',').map(x => { const p=x.trim().split(/\s+/); return {u:p[0], w:Number((p[1]||'').replace(/\D/g,''))||0} }).sort((a,b)=>b.w-a.w)[0]?.u || '';
  const qualifies = (r) => r.width >= vw*.60 && r.height >= Math.max(180,vh*.23) && r.top < vh && r.bottom > 0;
  const rect = (r) => ({x:Math.round(r.x), y:Math.round(r.y), width:Math.round(r.width), height:Math.round(r.height)});
  const out=[];
  document.querySelectorAll('img').forEach((img, i) => {
    const r=img.getBoundingClientRect(); if(!qualifies(r)) return;
    const rendered=absolute(img.currentSrc || img.src || '');
    const source=[largest(img.dataset.srcset || img.dataset.lazySrcset), img.dataset.src, img.dataset.lazySrc,
      largest(img.getAttribute('srcset')), rendered, img.getAttribute('src')].map(absolute).find(Boolean);
    if(source) out.push({kind:'img', source_url:source, rendered_url:rendered || source, alt:img.alt || '',
      link_url:absolute(img.closest('a[href]')?.href || ''), natural_width:img.naturalWidth||null,
      natural_height:img.naturalHeight||null, dom_order:i, ...rect(r)});
  });
  const selectors='[style*="background"],[class*="banner" i],[class*="hero" i],[class*="slide" i],[class*="carousel" i],[class*="swiper" i]';
  document.querySelectorAll(selectors).forEach((el,i) => {
    const r=el.getBoundingClientRect(); if(!qualifies(r)) return;
    [getComputedStyle(el),getComputedStyle(el,'::before'),getComputedStyle(el,'::after')].forEach((style,j) => {
      for(const match of (style.backgroundImage||'').matchAll(/url\(["']?(.*?)["']?\)/g)) {
        const source=absolute(match[1]); if(source) out.push({kind:j?'background-pseudo':'background',source_url:source,
          rendered_url:source,alt:el.getAttribute('aria-label')||'',link_url:absolute(el.closest('a[href]')?.href||''),
          natural_width:null,natural_height:null,dom_order:100000+i,...rect(r)});
      }
    });
  });
  const unique=[...new Map(out.map(x=>[x.source_url,x])).values()].sort((a,b)=>a.y-b.y || b.width*b.height-a.width*a.height || a.dom_order-b.dom_order);
  if(!unique.length) return [];
  const heroTop=unique[0].y;
  return unique.filter(x=>x.y<=heroTop+100);
}
"""

CLICK_NEXT_JS = r"""
() => {
  const pattern=/(next|pr[oó]xim[oa]|seguinte|avançar|arrow.?right|chevron.?right)/i;
  for(const el of document.querySelectorAll('button,[role="button"],.swiper-button-next,.slick-next')) {
    const label=[el.getAttribute('aria-label'),el.title,el.className,el.textContent].filter(Boolean).join(' ');
    const r=el.getBoundingClientRect();
    if(pattern.test(label) && !el.disabled && r.top<innerHeight && r.bottom>0 && r.left<innerWidth && r.right>0) {
      el.click(); return label.slice(0,160);
    }
  }
  return null;
}
"""

CAROUSEL_INFO_JS = r"""
() => {
  let declared=null;
  document.querySelectorAll('[aria-label]').forEach(el => {
    const m=(el.getAttribute('aria-label')||'').match(/(?:dot|slide)\s+\d+\s+(?:of|de)\s+(\d+)/i);
    if(m) declared=Math.max(declared||0,Number(m[1]));
  });
  const videos=[];
  document.querySelectorAll('video').forEach(v => {
    const r=v.getBoundingClientRect();
    if(r.width>=innerWidth*.60 && r.height>=180 && r.top<innerHeight && r.bottom>0) {
      const source=v.currentSrc||v.src||v.querySelector('source[src]')?.src||''; if(source) videos.push(source);
    }
  });
  return {declared_slides:declared,video_slides:[...new Set(videos)]};
}
"""

DISMISS_OVERLAYS_JS = r"""
() => { let n=0; document.querySelectorAll('[role="dialog"] button,[aria-modal="true"] button').forEach(b => {
  if(/^(aceitar( todos)?|aceito|permitir todos|concordo|continuar)$/i.test((b.textContent||b.getAttribute('aria-label')||'').trim())) { b.click(); n++; }
}); return n; }
"""


def is_safe_public_http_url(url: str, *, resolve_dns: bool = True) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return False
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            return False
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            if not resolve_dns:
                return True
            try:
                addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
            except (OSError, ValueError):
                return False
        return bool(addresses) and all(addr.is_global for addr in addresses)
    except (TypeError, ValueError):
        return False


def _cancelled(cancel_event: Any) -> bool:
    return bool(cancel_event and cancel_event.is_set())


def normalize_image_content_type(content_type: str, url: str, body: bytes) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized in KNOWN_IMAGE_MIME:
        return normalized
    suffix = urlparse(url).path.lower()
    for extension, mime in MIME_BY_SUFFIX.items():
        if suffix.endswith(extension):
            return mime
    head = body[:32]
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return "image/webp"
    if b"ftypavif" in head or b"ftypavis" in head:
        return "image/avif"
    if body.lstrip()[:4].lower() == b"<svg":
        return "image/svg+xml"
    raise ValueError(f"unsupported banner content type: {content_type or 'missing'}")


@dataclass
class BrandExtractionResult:
    banners: list[BannerCandidate]
    videos: list[BannerVideoSlide]
    screenshot_asset: StoredBannerAsset
    final_url: str


AssetFetcher = Callable[[Any, str, str], tuple[bytes, str]]


class BannerExtractionService:
    def __init__(
        self,
        storage: BannerStorageService = banner_storage_service,
        *,
        max_slides: int = MAX_SLIDES,
        settle_ms: int = SETTLE_MS,
        asset_fetcher: Optional[AssetFetcher] = None,
    ):
        self.storage = storage
        self.max_slides = max_slides
        self.settle_ms = settle_ms
        self.asset_fetcher = asset_fetcher or self._fetch_asset

    def extract_brand(
        self,
        browser: Any,
        brand: Any,
        cancel_event: Any = None,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> BrandExtractionResult:
        if _cancelled(cancel_event):
            raise InterruptedError("banner extraction cancelled")
        brand_key = getattr(brand, "brand_key", None) or brand["brand_key"]
        brand_name = getattr(brand, "brand_name", None) or brand["brand_name"]
        domain = getattr(brand, "domain", None) or brand["domain"]
        page_url = f"https://{domain.strip('/')}"
        if not is_safe_public_http_url(page_url):
            raise ValueError("brand domain does not resolve to a public HTTP(S) target")

        context = browser.new_context(
            viewport=VIEWPORT, locale="pt-BR", timezone_id="America/Sao_Paulo",
            user_agent=USER_AGENT, java_script_enabled=True,
            extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"},
        )
        page = context.new_page()
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS)
            if _cancelled(cancel_event):
                raise InterruptedError("banner extraction cancelled")
            page.wait_for_timeout(self.settle_ms)
            page.evaluate(DISMISS_OVERLAYS_JS)
            page.wait_for_timeout(500)
            return self.collect_page(page, brand_key, brand_name, cancel_event, progress_callback)
        finally:
            page.close()
            context.close()

    def collect_page(
        self,
        page: Any,
        brand_key: str,
        brand_name: str,
        cancel_event: Any = None,
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> BrandExtractionResult:
        if _cancelled(cancel_event):
            raise InterruptedError("banner extraction cancelled")
        screenshot = self.storage.store_asset(page.screenshot(full_page=False), "image/png")
        collected: dict[str, dict] = {}
        video_urls: list[str] = []
        no_new_rounds = 0
        declared_slides = None

        for attempt in range(self.max_slides + 1):
            if _cancelled(cancel_event):
                raise InterruptedError("banner extraction cancelled")
            info = page.evaluate(CAROUSEL_INFO_JS)
            declared_slides = info.get("declared_slides") or declared_slides
            for url in info.get("video_slides", []):
                absolute = urljoin(page.url, url)
                if absolute not in video_urls:
                    video_urls.append(absolute)
            previous = len(collected)
            for item in page.evaluate(COLLECT_BANNERS_JS):
                if item["source_url"] not in collected:
                    item["discovered_on_attempt"] = attempt
                    collected[item["source_url"]] = item
            no_new_rounds = no_new_rounds + 1 if len(collected) == previous else 0
            if progress_callback:
                progress_callback({"kind": "discovery", "attempt": attempt, "banner_count": len(collected), "video_count": len(video_urls)})
            if attempt >= self.max_slides:
                break
            if declared_slides is None and no_new_rounds >= 2:
                break
            if declared_slides is not None and attempt >= declared_slides - 1:
                break
            if not page.evaluate(CLICK_NEXT_JS):
                break
            page.wait_for_timeout(800)

        banners: list[BannerCandidate] = []
        for order, item in enumerate(collected.values(), start=1):
            if _cancelled(cancel_event):
                raise InterruptedError("banner extraction cancelled")
            source_url = item["source_url"]
            rendered_url = item.get("rendered_url") or source_url
            if not is_safe_public_http_url(source_url):
                continue
            # The URL must have been discovered in this page. Cross-host CDNs are valid;
            # arbitrary caller-supplied URLs never enter this method.
            body, content_type = self.asset_fetcher(page.context, source_url, page.url)
            if _cancelled(cancel_event):
                raise InterruptedError("banner extraction cancelled")
            asset = self.storage.store_asset(body, content_type)
            description = item.get("alt") or f"banner-{order}"
            banners.append(BannerCandidate(
                banner_id=f"{brand_key}-{order}-{asset.sha256[:12]}", brand_key=brand_key,
                brand_name=brand_name, slide_order=order,
                friendly_filename=friendly_banner_filename(order, description, brand_name, asset.extension),
                asset=asset, source_url=source_url, rendered_url=rendered_url,
                click_url=item.get("link_url") or None, alt_text=item.get("alt") or None,
                dom_kind=item.get("kind", "img"), rendered_width=item.get("width"),
                rendered_height=item.get("height"), natural_width=item.get("natural_width"),
                natural_height=item.get("natural_height"),
            ))
            if progress_callback:
                progress_callback({"kind": "banner", "banner": banners[-1].model_dump(mode="json")})

        videos = [BannerVideoSlide(brand_key=brand_key, slide_order=i, source_url=url) for i, url in enumerate(video_urls, 1)]
        return BrandExtractionResult(banners=banners, videos=videos, screenshot_asset=screenshot, final_url=page.url)

    def _fetch_asset(self, context: Any, url: str, referer: str) -> tuple[bytes, str]:
        response = context.request.get(url, headers={"Referer": referer}, timeout=NAVIGATION_TIMEOUT_MS)
        if not response.ok:
            raise RuntimeError(f"banner download failed with HTTP {response.status}")
        if not is_safe_public_http_url(response.url):
            raise ValueError("banner download redirected to a non-public target")
        body = response.body()
        if len(body) > self.storage.max_asset_bytes:
            raise ValueError("banner asset exceeds configured byte limit")
        return body, normalize_image_content_type(response.headers.get("content-type", ""), response.url, body)


banner_extraction_service = BannerExtractionService()
