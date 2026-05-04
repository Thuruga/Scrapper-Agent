"""
Orquestrador Multi-Marca.

Executa varreduras de categoria em paralelo para múltiplas marcas,
consolidando os resultados em um único arquivo Excel.

Fluxo:
    1. Recebe mapeamento {brand → url} do CategoryMapping
    2. Cria N threads, cada uma rodando o orquestrador padrão
    3. Consolida logs via WebSocket com prefixo por marca
    4. Gera Excel unificado com coluna `brand`
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

import pandas as pd

from config import settings, BRAND_REGISTRY
from crawler import varrer_categoria_vtex
from scrapers import get_scraper

logger = logging.getLogger("OrchestratorMulti")


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
@dataclass
class BrandJobResult:
    """Resultado da varredura de uma marca."""
    brand_key: str
    brand_name: str
    products: list = field(default_factory=list)
    total_links: int = 0
    success_count: int = 0
    error_count: int = 0
    error_message: Optional[str] = None
    finished: bool = False


# ---------------------------------------------------------------------------
# Per-brand worker (runs in its own asyncio event loop in a thread)
# ---------------------------------------------------------------------------
async def _run_brand_pipeline(
    brand_key: str,
    url: str,
    cancel_event: threading.Event,
    log_callback: Optional[Callable] = None,
) -> BrandJobResult:
    """
    Pipeline completo para uma marca: crawl → scrape → retorna produtos.
    """
    brand_info = BRAND_REGISTRY.get(brand_key, {})
    brand_name = brand_info.get("name", brand_key.title())
    result = BrandJobResult(brand_key=brand_key, brand_name=brand_name)

    def emit(msg_dict):
        if log_callback:
            # Injeta brand_key no log para o frontend distinguir
            msg_dict["brand"] = brand_key
            msg_dict["brand_name"] = brand_name
            log_callback(msg_dict)

    def is_cancelled() -> bool:
        return cancel_event.is_set()

    # ── Carregar scraper ───────────────────────────────────────────────
    try:
        scraper_module = get_scraper(brand_key)
    except ValueError as e:
        result.error_message = str(e)
        result.finished = True
        emit({"type": "error", "message": f"[{brand_name}] {e}"})
        return result

    # ── ETAPA 1: VARREDURA ─────────────────────────────────────────────
    emit({"type": "info", "message": f"[{brand_name}] Iniciando varredura: {url}"})

    links = await varrer_categoria_vtex(
        url,
        log_callback=lambda msg: emit(
            msg if isinstance(msg, dict) else {"type": "info", "message": f"[{brand_name}] {msg}"}
        ),
        cancel_event=cancel_event,
    )

    if is_cancelled():
        emit({"type": "cancelled", "message": f"[{brand_name}] Varredura cancelada."})
        result.finished = True
        return result

    if not links:
        emit({"type": "error", "message": f"[{brand_name}] Nenhum link encontrado."})
        result.finished = True
        return result

    result.total_links = len(links)
    emit({
        "type": "brand_stats",
        "total_links": len(links),
        "message": f"[{brand_name}] {len(links)} links encontrados. Iniciando extração...",
    })

    # ── ETAPA 2: EXTRAÇÃO ──────────────────────────────────────────────
    semaforo = asyncio.Semaphore(settings.MAX_CONCURRENCY)

    async def extract_one(link: str):
        if is_cancelled():
            return None
        async with semaforo:
            if is_cancelled():
                return None
            emit({"type": "info", "message": f"[{brand_name}] Extraindo: {link}"})
            try:
                produto = await scraper_module.scrape_competitor_product(link, brand_key)
                await asyncio.sleep(settings.SCRAPER_DELAY_SECONDS)
                if produto:
                    result.success_count += 1
                    emit({"type": "brand_success", "message": f"[{brand_name}] ✓ {produto.raw_title}"})
                else:
                    result.error_count += 1
                    emit({"type": "brand_error", "message": f"[{brand_name}] ✗ Falha: {link}"})
                return produto
            except asyncio.CancelledError:
                return None
            except Exception as e:
                result.error_count += 1
                emit({"type": "brand_error", "message": f"[{brand_name}] ✗ Erro: {e}"})
                return None

    tasks = [extract_one(link) for link in links]
    resultados_brutos = await asyncio.gather(*tasks)

    result.products = [r for r in resultados_brutos if r is not None]
    result.finished = True

    emit({
        "type": "brand_done",
        "message": f"[{brand_name}] Concluído: {result.success_count} produtos extraídos.",
        "success_count": result.success_count,
        "error_count": result.error_count,
    })

    return result


# ---------------------------------------------------------------------------
# Thread wrapper
# ---------------------------------------------------------------------------
def _thread_worker(
    brand_key: str,
    url: str,
    cancel_event: threading.Event,
    log_callback: Optional[Callable],
    results_store: Dict[str, BrandJobResult],
):
    """Executa o pipeline de uma marca em uma thread separada com seu próprio event loop."""
    try:
        result = asyncio.run(
            _run_brand_pipeline(brand_key, url, cancel_event, log_callback)
        )
        results_store[brand_key] = result
    except Exception as e:
        logger.error(f"Thread {brand_key} falhou: {e}")
        results_store[brand_key] = BrandJobResult(
            brand_key=brand_key,
            brand_name=brand_key.title(),
            error_message=str(e),
            finished=True,
        )


# ---------------------------------------------------------------------------
# Public: Multi-Brand Orchestrator
# ---------------------------------------------------------------------------
def run_multi_orchestrator_sync(
    job_id: str,
    brand_url_map: Dict[str, str],
    category_label: str,
    main_loop: asyncio.AbstractEventLoop,
    cancel_event: threading.Event,
):
    """
    Ponto de entrada para o background task do FastAPI.

    Cria N threads (uma por marca), espera todas finalizarem,
    consolida os resultados em Excel e envia log final via WebSocket.
    """
    from core.websocket import manager
    from core.job_manager import JOB_CANCEL_FLAGS

    def log_callback(msg_dict):
        asyncio.run_coroutine_threadsafe(
            manager.send_message(msg_dict, job_id), main_loop
        )

    log_callback({
        "type": "info",
        "message": f"Iniciando varredura multi-marca para '{category_label}': {list(brand_url_map.keys())}",
    })

    # ── Lançar threads ─────────────────────────────────────────────────
    results_store: Dict[str, BrandJobResult] = {}
    threads: List[threading.Thread] = []

    for brand_key, url in brand_url_map.items():
        t = threading.Thread(
            target=_thread_worker,
            args=(brand_key, url, cancel_event, log_callback, results_store),
            name=f"scraper-{brand_key}",
            daemon=True,
        )
        threads.append(t)
        t.start()

    # ── Aguardar todas as threads ──────────────────────────────────────
    for t in threads:
        t.join()

    # ── Consolidar resultados ──────────────────────────────────────────
    is_cancelled = cancel_event.is_set()

    all_products = []
    total_success = 0
    total_errors = 0

    for brand_key, result in results_store.items():
        total_success += result.success_count
        total_errors += result.error_count
        for produto in result.products:
            row = produto.model_dump()
            row["brand"] = result.brand_name
            all_products.append(row)

    # ── Gerar Excel ────────────────────────────────────────────────────
    slug = category_label.lower().replace(" ", "_").replace("&", "e")
    timestamp = int(time.time())
    arquivo_saida = f"dados_multimarca_{slug}_{timestamp}.xlsx"

    if all_products:
        df = pd.DataFrame(all_products)

        # Mover coluna 'brand' para a primeira posição
        cols = df.columns.tolist()
        if "brand" in cols:
            cols.remove("brand")
            cols.insert(0, "brand")
            df = df[cols]

        # Expandir specifications
        if "specifications" in df.columns:
            specs_df = df["specifications"].apply(pd.Series)
            df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)

        # Ordenar por marca e preço
        sort_cols = []
        if "brand" in df.columns:
            sort_cols.append("brand")
        if "price_full" in df.columns:
            sort_cols.append("price_full")
        if sort_cols:
            df = df.sort_values(sort_cols, na_position="last")

        df.to_excel(arquivo_saida, index=False)

        msg_type = "cancelled_done" if is_cancelled else "done"
        log_callback({
            "type": msg_type,
            "valid_products": len(all_products),
            "total_success": total_success,
            "total_errors": total_errors,
            "output_file": arquivo_saida,
            "brands_completed": list(results_store.keys()),
            "message": (
                f"{'Cancelado parcial' if is_cancelled else 'Concluído'}! "
                f"{len(all_products)} produtos de "
                f"{len(results_store)} marcas salvos em {arquivo_saida}."
            ),
        })
    else:
        msg_type = "cancelled" if is_cancelled else "error_done"
        log_callback({
            "type": msg_type,
            "message": (
                "Operação cancelada. Nenhum produto coletado."
                if is_cancelled
                else "Nenhum produto válido extraído de nenhuma marca."
            ),
        })

    # Cleanup
    JOB_CANCEL_FLAGS.pop(job_id, None)
