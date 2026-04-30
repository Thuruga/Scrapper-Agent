import asyncio
import json
import importlib
import pandas as pd
from crawler import varrer_categoria_vtex


async def extrair_com_limite(semaforo, url, marca, scraper_module, log_callback=None):
    """
    Função Worker: Só executa se o semáforo autorizar (limite de concorrência)
    """
    async with semaforo:
        if log_callback:
            log_callback({"type": "info", "message": f"Iniciando extração: {url}"})
        try:
            resultado = await scraper_module.scrape_competitor_product(url, marca)
            # Pequena pausa entre cada extração para parecer humano e evitar bans
            await asyncio.sleep(2)
            if resultado and log_callback:
                log_callback({"type": "success", "message": f"Sucesso: {resultado.raw_title}"})
            elif not resultado and log_callback:
                log_callback({"type": "error", "message": f"Falha na extração de {url}"})
            return resultado
        except Exception as e:
            if log_callback:
                log_callback({"type": "error", "message": f"Erro fatal em {url}: {e}"})
            return None


async def run_orchestrator(marca: str, url_categoria: str, log_callback=None):
    def emit_log(msg):
        print(msg)
        if log_callback:
            # Verifica se já é um dicionário formatado, senão formata como string info
            if isinstance(msg, dict):
                log_callback(msg)
            else:
                log_callback({"type": "info", "message": msg})

    # Mapeamento para importar o módulo correto
    brand_map = {"aramis": "aramis", "reserva": "reserva", "tommy": "tommy"}
    module_name = brand_map.get(marca.lower().split()[0]) # 'Reserva' ou 'Reserva (Azzas 2154)' -> 'reserva'
    
    if not module_name:
        emit_log({"type": "error", "message": f"Marca não suportada: {marca}"})
        return
        
    scraper_module = importlib.import_module(module_name)

    arquivo_saida = f"dados_{module_name}_categoria.xlsx"

    emit_log("==================================================")
    emit_log(f" ETAPA 1: VARRENDO CATEGORIA ({marca})")
    emit_log("==================================================")

    # 1. Pega todos os links usando o seu spider
    def crawler_log(msg):
        emit_log(msg)
        
    links = await varrer_categoria_vtex(url_categoria, log_callback=crawler_log)

    if not links:
        emit_log({"type": "error", "message": "Nenhum link encontrado. Abortando operação."})
        return

    emit_log("\n==================================================")
    emit_log({"type": "stats", "total_links": len(links), "message": f"ETAPA 2: EXTRAÇÃO DE DADOS (Total: {len(links)} links)"})
    emit_log("==================================================")

    # 2. Configura a catraca (Semáforo) para no máximo 3 abas simultâneas
    concorrencia_maxima = 3
    semaforo = asyncio.Semaphore(concorrencia_maxima)
    emit_log(f"Iniciando extração com {concorrencia_maxima} robôs simultâneos...")

    # 3. Cria a lista de tarefas
    tarefas = [extrair_com_limite(semaforo, link, marca, scraper_module, log_callback=emit_log) for link in links]

    # 4. Executa todas as tarefas (o semáforo vai controlando o tráfego)
    resultados_brutos = await asyncio.gather(*tarefas)

    emit_log("\n==================================================")
    emit_log(" ETAPA 3: CONSOLIDAÇÃO E SALVAMENTO")
    emit_log("==================================================")

    # 5. Filtra quem falhou (None) e converte os objetos Pydantic para dicionários
    produtos_validos = []
    for res in resultados_brutos:
        if res:
            produtos_validos.append(res.model_dump())

    # 6. Salva tudo em um arquivo Excel usando pandas
    if produtos_validos:
        df = pd.DataFrame(produtos_validos)
        
        # Opcional: Expandir o dicionário de specifications para colunas separadas
        if 'specifications' in df.columns:
            specs_df = df['specifications'].apply(pd.Series)
            df = pd.concat([df.drop('specifications', axis=1), specs_df], axis=1)

        df.to_excel(arquivo_saida, index=False)
    else:
        emit_log({"type": "error", "message": "Nenhum produto válido extraído."})

    emit_log({"type": "done", "valid_products": len(produtos_validos), "output_file": arquivo_saida, "message": f"Sucesso! Dados de {len(produtos_validos)} produtos salvos em {arquivo_saida}."})
    emit_log("Pipeline de Camada Bronze concluído.")


async def main():
    marca = "Aramis"
    url_categoria = "https://www.aramis.com.br/roupas/polos"
    await run_orchestrator(marca, url_categoria)

if __name__ == "__main__":
    asyncio.run(main())
