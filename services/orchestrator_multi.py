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
import aiohttp
from config import BRAND_REGISTRY
from services.vtex_extractor import extrair_pagina_categoria

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
    Pipeline completo para uma marca: extração paginada da API VTEX.
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

    emit({"type": "info", "message": f"[{brand_name}] Iniciando extração rápida API: {url}"})

    pagina = 1
    
    async with aiohttp.ClientSession() as session:
        while True:
            if is_cancelled():
                emit({"type": "cancelled", "message": f"[{brand_name}] Operação interrompida."})
                break

            emit({"type": "info", "message": f"[{brand_name}] A extrair Página {pagina}..."})
            
            produtos_pagina = await extrair_pagina_categoria(session, url, brand_name, pagina)

            if not produtos_pagina:
                emit({"type": "info", "message": f"[{brand_name}] Fim da categoria alcançado na página {pagina}."})
                break

            result.products.extend(produtos_pagina)
            result.success_count += len(produtos_pagina)
            
            emit({"type": "brand_success", "message": f"[{brand_name}] Página {pagina} concluída. +{len(produtos_pagina)} produtos."})
            
            pagina += 1

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
