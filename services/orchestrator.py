"""
Orquestrador de Extração em Lote.

Pipeline: Varredura de categoria → Extração paralela → Consolidação em Excel.
Suporta cancelamento gracioso com salvamento de dados parciais.
"""

import asyncio
import threading
from typing import Optional, Callable

import pandas as pd

from config import settings
from crawler import varrer_categoria_vtex
from scrapers import get_scraper


async def extrair_com_limite(
    semaforo: asyncio.Semaphore,
    url: str,
    marca: str,
    scraper_module,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    """
    Função Worker: Só executa se o semáforo autorizar (limite de concorrência).
    Verifica o cancel_event antes de iniciar para parar rapidamente quando solicitado.
    """
    # Verifica cancelamento ANTES de adquirir o semáforo
    if cancel_event and cancel_event.is_set():
        return None

    async with semaforo:
        # Verifica novamente dentro do semáforo
        if cancel_event and cancel_event.is_set():
            return None

        if log_callback:
            log_callback({"type": "info", "message": f"Iniciando extração: {url}"})
        try:
            resultado = await scraper_module.scrape_competitor_product(url, marca)
            # Pequena pausa entre cada extração para parecer humano e evitar bans
            await asyncio.sleep(settings.SCRAPER_DELAY_SECONDS)
            if resultado and log_callback:
                log_callback({"type": "success", "message": f"Sucesso: {resultado.raw_title}"})
            elif not resultado and log_callback:
                log_callback({"type": "error", "message": f"Falha na extração de {url}"})
            return resultado
        except asyncio.CancelledError:
            return None
        except Exception as e:
            if log_callback:
                log_callback({"type": "error", "message": f"Erro fatal em {url}: {e}"})
            return None


async def run_orchestrator(
    marca: str,
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    def emit_log(msg):
        if log_callback:
            if isinstance(msg, dict):
                log_callback(msg)
            else:
                log_callback({"type": "info", "message": str(msg)})

    def is_cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    # Carrega o módulo do scraper via registry
    try:
        scraper_module = get_scraper(marca)
    except ValueError as e:
        emit_log({"type": "error", "message": str(e)})
        return

    # Nome do módulo para arquivo de saída
    module_key = marca.lower().split()[0]
    arquivo_saida = f"dados_{module_key}_categoria.xlsx"

    # ── ETAPA 1: VARREDURA DE CATEGORIA ────────────────────────────────────
    emit_log("==================================================")
    emit_log(f" ETAPA 1: VARRENDO CATEGORIA ({marca})")
    emit_log("==================================================")

    links = await varrer_categoria_vtex(
        url_categoria,
        log_callback=emit_log,
        cancel_event=cancel_event,
    )

    if is_cancelled():
        emit_log({"type": "cancelled", "message": "Operação cancelada pelo usuário durante a varredura."})
        return

    if not links:
        emit_log({"type": "error", "message": "Nenhum link encontrado. Abortando operação."})
        return

    emit_log("\n==================================================")
    emit_log({
        "type": "stats",
        "total_links": len(links),
        "message": f"ETAPA 2: EXTRAÇÃO DE DADOS (Total: {len(links)} links)",
    })
    emit_log("==================================================")

    # ── ETAPA 2: EXTRAÇÃO DE DADOS ─────────────────────────────────────────
    concorrencia_maxima = settings.MAX_CONCURRENCY
    semaforo = asyncio.Semaphore(concorrencia_maxima)
    emit_log(f"Iniciando extração com {concorrencia_maxima} robôs simultâneos...")

    tarefas = [
        extrair_com_limite(
            semaforo, link, marca, scraper_module,
            log_callback=emit_log,
            cancel_event=cancel_event,
        )
        for link in links
    ]

    resultados_brutos = await asyncio.gather(*tarefas)

    if is_cancelled():
        # Ainda salva o que já foi coletado antes de cancelar
        emit_log({"type": "cancelled", "message": "Operação cancelada. Salvando os dados coletados até agora..."})

    # ── ETAPA 3: CONSOLIDAÇÃO ───────────────────────────────────────────────
    emit_log("\n==================================================")
    emit_log(" ETAPA 3: CONSOLIDAÇÃO E SALVAMENTO")
    emit_log("==================================================")

    produtos_validos = [res.model_dump() for res in resultados_brutos if res]

    if produtos_validos:
        df = pd.DataFrame(produtos_validos)
        if "specifications" in df.columns:
            specs_df = df["specifications"].apply(pd.Series)
            df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
        df.to_excel(arquivo_saida, index=False)

        if is_cancelled():
            emit_log({
                "type": "cancelled_done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"Cancelado. Salvos {len(produtos_validos)} produtos parciais em {arquivo_saida}.",
            })
        else:
            emit_log({
                "type": "done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"Sucesso! Dados de {len(produtos_validos)} produtos salvos em {arquivo_saida}.",
            })
    else:
        if is_cancelled():
            emit_log({"type": "cancelled", "message": "Operação cancelada. Nenhum produto foi coletado."})
        else:
            emit_log({"type": "error", "message": "Nenhum produto válido extraído."})

    emit_log("Pipeline de Camada Bronze concluído.")


async def main():
    marca = "Aramis"
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    await run_orchestrator(marca, url_categoria)


if __name__ == "__main__":
    asyncio.run(main())
