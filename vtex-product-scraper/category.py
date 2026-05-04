"""
Orquestrador de Extração em Lote (Alta Performance).

Pipeline: Varredura de Categoria via API VTEX (Intelligent Search) → Consolidação em Excel.
Suporta cancelamento gracioso com salvamento de dados parciais.
"""

import asyncio
import threading
from typing import Optional, Callable
import pandas as pd
import aiohttp

# Importa o novo motor de extração focado em API
from services.vtex_extractor import extrair_pagina_categoria

async def run_orchestrator(
    marca: str,
    url_categoria: str,
    log_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
):
    def emit_log(msg):
        """Função auxiliar para emissão de logs estruturados ou em texto."""
        if log_callback:
            if isinstance(msg, dict): 
                log_callback(msg)
            else: 
                log_callback({"type": "info", "message": str(msg)})

    def is_cancelled() -> bool:
        """Verifica se o utilizador solicitou o cancelamento da extração."""
        return cancel_event is not None and cancel_event.is_set()

    # Define o nome do ficheiro de saída (ex: dados_aramis_categoria.xlsx)
    module_key = marca.lower().split()[0]
    arquivo_saida = f"dados_{module_key}_categoria.xlsx"

    # ── ETAPA 1: INICIALIZAÇÃO DA EXTRAÇÃO VIA API ──────────────────────────
    emit_log("==================================================")
    emit_log(f" INICIANDO EXTRAÇÃO DE ALTA PERFORMANCE: {marca}")
    emit_log(f" Alvo: {url_categoria}")
    emit_log("==================================================")

    produtos_totais = []
    pagina = 1

    # Inicia a sessão HTTP uma única vez para garantir a máxima velocidade
    async with aiohttp.ClientSession() as session:
        while True:
            # Verificação de cancelamento antes de cada página
            if is_cancelled():
                emit_log({"type": "cancelled", "message": "Operação interrompida pelo utilizador."})
                break

            emit_log({"type": "info", "message": f"A extrair Página {pagina}..."})
            
            try:
                # Pede à API a página completa (já devolve a lista de objetos limpos!)
                produtos_pagina = await extrair_pagina_categoria(session, url_categoria, marca, pagina)
            except Exception as e:
                emit_log({"type": "error", "message": f"Erro fatal ao consultar a página {pagina}: {e}"})
                break

            # Se a API devolver uma lista vazia, significa que chegámos ao fim da categoria
            if not produtos_pagina:
                emit_log({"type": "info", "message": f"Fim da categoria alcançado na página {pagina}."})
                break

            produtos_totais.extend(produtos_pagina)
            emit_log({"type": "success", "message": f"Página {pagina} concluída. +{len(produtos_pagina)} produtos capturados."})
            
            pagina += 1

    # ── ETAPA 2: CONSOLIDAÇÃO E EXPORTAÇÃO PARA A CAMADA BRONZE ─────────────
    emit_log("\n==================================================")
    emit_log(" A GERAR DADOS PARA A CAMADA BRONZE (EXCEL)")
    emit_log("==================================================")

    # Converte os modelos Pydantic para dicionários
    produtos_validos = [res.model_dump() for res in produtos_totais if res]

    if produtos_validos:
        df = pd.DataFrame(produtos_validos)
        
        # Converte as listas de cores e tamanhos para strings separadas por vírgula para suportar o formato Excel
        if 'available_colors' in df.columns:
            df['available_colors'] = df['available_colors'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        if 'available_sizes' in df.columns:
            df['available_sizes'] = df['available_sizes'].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
        
        # Expande o dicionário de especificações em colunas separadas
        if "specifications" in df.columns:
            specs_df = df["specifications"].apply(pd.Series)
            df = pd.concat([df.drop("specifications", axis=1), specs_df], axis=1)
            
        # Guarda o resultado final no disco
        df.to_excel(arquivo_saida, index=False)

        if is_cancelled():
            emit_log({
                "type": "cancelled_done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"Cancelamento concluído. Salvos {len(produtos_validos)} produtos parciais em {arquivo_saida}.",
            })
        else:
            emit_log({
                "type": "done",
                "valid_products": len(produtos_validos),
                "output_file": arquivo_saida,
                "message": f"GOLAÇO! Dados de {len(produtos_validos)} produtos salvos em {arquivo_saida} numa fração do tempo.",
            })
    else:
        emit_log({"type": "error", "message": "Nenhum produto foi extraído no total."})


# ---------------------------------------------------------------------------
# Ponto de Entrada para Testes Locais
# ---------------------------------------------------------------------------
async def main():
    """Função para testar o orquestrador diretamente no terminal."""
    marca_teste = "Aramis"
    url_teste = "https://www.aramis.com.br/roupas/polos"
    
    # Callback simples para imprimir no terminal se não estivermos a usar a API/WebSockets
    def console_logger(msg):
        if isinstance(msg, dict):
            print(f"[{msg.get('type', 'info').upper()}] {msg.get('message', '')}")
        else:
            print(msg)

    await run_orchestrator(marca_teste, url_teste, log_callback=console_logger)

if __name__ == "__main__":
    asyncio.run(main())