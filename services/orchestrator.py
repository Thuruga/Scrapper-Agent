import asyncio
import threading
from typing import Optional, Callable
import pandas as pd
import aiohttp

# Importamos o nosso novo motor!
from services.vtex_extractor import extrair_pagina_categoria

async def run_orchestrator(
    marca: str,
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    def emit_log(msg):
        if log_callback:
            if isinstance(msg, dict): log_callback(msg)
            else: log_callback({"type": "info", "message": str(msg)})

    def is_cancelled() -> bool:
        return cancel_event is not None and cancel_event.is_set()

    module_key = marca.lower().split()[0]
    arquivo_saida = f"dados_{module_key}_categoria.xlsx"

    emit_log("==================================================")
    emit_log(f" INICIANDO EXTRAÇÃO DE ALTA PERFORMANCE: {marca}")
    emit_log(f" Alvo: {url_categoria}")
    emit_log("==================================================")

    produtos_totais = []
    pagina = 1

    # Inicia a sessão HTTP uma única vez para máxima velocidade
    async with aiohttp.ClientSession() as session:
        while True:
            if is_cancelled():
                emit_log({"type": "cancelled", "message": "Operação interrompida pelo utilizador."})
                break

            emit_log({"type": "info", "message": f"A extrair Página {pagina}..."})
            
            # Pede à API a página completa (já devolve a lista de objetos limpos!)
            produtos_pagina = await extrair_pagina_categoria(session, url_categoria, marca, pagina)

            if not produtos_pagina:
                emit_log({"type": "info", "message": f"Fim da categoria alcançado na página {pagina}."})
                break

            produtos_totais.extend(produtos_pagina)
            emit_log({"type": "success", "message": f"Página {pagina} concluída. +{len(produtos_pagina)} produtos."})
            
            pagina += 1

    # ── ETAPA FINAL: CONSOLIDAÇÃO ───────────────────────────────────────────────
    emit_log("\n==================================================")
    emit_log(" A GERAR DADOS PARA A CAMADA BRONZE (EXCEL)")
    emit_log("==================================================")

    produtos_validos = [res.model_dump() for res in produtos_totais if res]

    if produtos_validos:
        df = pd.DataFrame(produtos_validos)
        
        # Converte as listas de cores e tamanhos para strings separadas por vírgula para caber no Excel
        df['available_colors'] = df['available_colors'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        df['available_sizes'] = df['available_sizes'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        
        if "specifications" in df.columns:
            specs_df = df["specifications"].apply(pd.Series)
            df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
            
        df.to_excel(arquivo_saida, index=False)

        if is_cancelled():
            emit_log({
                "type": "cancelled_done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"Cancelado. Salvos {len(produtos_validos)} produtos em {arquivo_saida}.",
            })
        else:
            emit_log({
                "type": "done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"GOLAÇO! Dados de {len(produtos_validos)} produtos salvos em {arquivo_saida} numa fração do tempo.",
            })
    else:
        emit_log({"type": "error", "message": "Nenhum produto extraído no total."})


async def main():
    marca = "Aramis"
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    await run_orchestrator(marca, url_categoria)


if __name__ == "__main__":
    asyncio.run(main())
