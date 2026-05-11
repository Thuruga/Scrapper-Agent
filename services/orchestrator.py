"""
Orquestrador de Extração em Lote.

Pipeline: Varredura de categoria → Extração paralela → Consolidação em Excel.
Suporta cancelamento gracioso com salvamento de dados parciais.
"""

import asyncio
import threading
import logging
from typing import Optional, Callable

import pandas as pd

logger = logging.getLogger("Orchestrator")


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

        if produtos_validos:
            df = pd.DataFrame(produtos_validos)
            
            # Converter listas para strings separadas por vírgula
            for col in ["available_colors", "available_sizes"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

            if "specifications" in df.columns:
                specs_df = df["specifications"].apply(pd.Series)
                df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
            
            df.to_excel(arquivo_saida, index=False)

            msg_type = "cancelled_done" if is_cancelled() else "done"
            emit_log({
                "type": msg_type,
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
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
