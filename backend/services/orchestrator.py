"""
Orquestrador de Extração em Lote.

Pipeline: Varredura de categoria → Extração paralela → Consolidação em Excel.
Suporta cancelamento gracioso com salvamento de dados parciais.
"""

import asyncio
import logging
from typing import Optional, Callable

import pandas as pd

from services.stock_summary_service import (
    compute_stock_summary,
    ensure_scan_product_ids,
    persist_category_job_stock_summaries,
)

logger = logging.getLogger("Orchestrator")


def _product_dict(product):
    if isinstance(product, dict):
        return dict(product)
    if hasattr(product, "model_dump"):
        return product.model_dump(mode="json")
    if hasattr(product, "dict"):
        return product.dict()
    return dict(vars(product))


async def run_orchestrator(
    marca: str,
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[asyncio.Event] = None,
    job_id: str | None = None,
):
    def emit_log(msg):
        if log_callback:
            if isinstance(msg, dict):
                log_callback(msg)
            else:
                log_callback({"type": "info", "message": str(msg)})
        else:
            logger.info(msg)

    def is_cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    # ── ETAPA 1: VARREDURA E EXTRAÇÃO PAGINADA ─────────────────────────────
    emit_log("==================================================")
    emit_log(f" ETAPA 1: VARRENDO CATEGORIA PAGINADA ({marca})")
    emit_log("==================================================")

    from services.engines.factory import engine_factory
    
    engine = engine_factory.get_engine(marca)
    produtos_validos = []
    
    # Nome do módulo para arquivo de saída
    module_key = marca.lower().split()[0]
    arquivo_saida = f"dados_{module_key}_categoria.xlsx"

    try:
        async for produto in engine.run_bulk_scrape(
            category_url=url_categoria,
            log_callback=emit_log,
            cancel_event=cancel_event
        ):
            produtos_validos.append(produto)
            
            # Se atingir um lote grande (ex: 500), poderíamos salvar parcial aqui.
            # Para simplificar e manter compatibilidade com o formato final,
            # consolidamos ao final, mas o processamento já é streaming.
            # O risco de memória é o array 'produtos_validos'.
            # Em uma implementação extrema, usaríamos ExcelWriter incremental.

        if is_cancelled() and not produtos_validos:
            emit_log({"type": "cancelled", "message": "Operação cancelada pelo usuário durante a varredura."})
            return

        # ── ETAPA 2: CONSOLIDAÇÃO E SALVAMENTO ──────────────────────────────────
        emit_log("\n==================================================")
        emit_log(" ETAPA 2: CONSOLIDAÇÃO E SALVAMENTO")
        emit_log("==================================================")

        stock_summary = None
        if job_id is not None:
            scan_id = f"{job_id}:{marca.lower()}"
            produtos_validos = ensure_scan_product_ids(
                produtos_validos,
                marca,
                scan_id,
            )
            stock_summary = compute_stock_summary(
                produtos_validos,
                brand=marca,
                scan_id=scan_id,
            )
            persist_category_job_stock_summaries(job_id, [stock_summary])

        if produtos_validos:
            df = pd.DataFrame([_product_dict(produto) for produto in produtos_validos])
            
            # Converter listas para strings separadas por vírgula
            for col in ["available_colors", "available_sizes"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

            if "specifications" in df.columns:
                # Tratar NaNs antes de expandir para evitar erros com pd.Series
                df["specifications"] = df["specifications"].apply(lambda x: x if isinstance(x, dict) else {})
                specs_df = df["specifications"].apply(pd.Series)
                df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
            
            # Offload da operação de I/O bloqueante (to_excel) para uma thread
            await asyncio.to_thread(df.to_excel, arquivo_saida, index=False)

            msg_type = "cancelled_done" if is_cancelled() else "done"
            emit_log({
                "type": msg_type,
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                **(
                    {"stock_summary": stock_summary.model_dump(mode="json")}
                    if stock_summary is not None
                    else {}
                ),
                "message": f"{'Cancelado. ' if is_cancelled() else ''}Sucesso! Dados de {len(produtos_validos)} produtos salvos em {arquivo_saida}.",
            })
        else:
            if is_cancelled():
                emit_log({"type": "cancelled", "message": "Operação cancelada. Nenhum produto foi coletado."})
            else:
                emit_log({"type": "error_done", "message": "Nenhum produto válido extraído."})
    except Exception as e:
        logger.error(f"Erro no orquestrador ({marca}): {e}")
        emit_log({"type": "error_done", "message": f"Erro crítico: {e}"})

    emit_log("Pipeline de Camada Bronze concluído.")


async def main():
    marca = "Aramis"
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    await run_orchestrator(marca, url_categoria)


if __name__ == "__main__":
    asyncio.run(main())
