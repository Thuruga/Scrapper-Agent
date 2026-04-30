import asyncio
import aiohttp
import json


async def extrair_arvore_categorias(nome_marca: str, dominio: str):
    print(f"\n[{nome_marca}] Conectando na API de Catálogo da VTEX...")
    url_api = f"https://{dominio}/api/catalog_system/pub/category/tree/3"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url_api, headers=headers, timeout=15) as response:
                if response.status == 200:
                    dados_arvore = await response.json()

                    lista_categorias_finais = []

                    # Função recursiva para descer os níveis da árvore
                    def varrer_nos(lista_nos, departamento=""):
                        for no in lista_nos:
                            nome_categoria = no.get("name")
                            url_categoria = no.get("url")
                            tem_filhos = no.get("hasChildren", False)
                            filhos = no.get("children", [])

                            # Se a URL não vier completa, nós a montamos
                            if url_categoria and url_categoria.startswith("/"):
                                url_categoria = f"https://{dominio}{url_categoria}"

                            # Se for uma categoria folha (sem filhos), nós salvamos para o Scraper
                            if not tem_filhos and url_categoria:
                                lista_categorias_finais.append(
                                    {
                                        "departamento": departamento or no.get("name"),
                                        "nome": nome_categoria,
                                        "url": url_categoria,
                                    }
                                )
                            # Se tiver filhos, desce um nível
                            elif tem_filhos:
                                varrer_nos(
                                    filhos, departamento=departamento or nome_categoria
                                )

                    # Inicia a varredura a partir da raiz
                    varrer_nos(dados_arvore)

                    print(
                        f"[{nome_marca}] Sucesso! {len(lista_categorias_finais)} URLs de categoria mapeadas."
                    )
                    return lista_categorias_finais
                else:
                    print(f"[{nome_marca}] Erro na API: Status {response.status}")
                    return []
    except Exception as e:
        print(f"[{nome_marca}] Falha de conexão: {e}")
        return []


async def main():
    # As três lojas operam na infraestrutura VTEX
    concorrentes = [
        {"marca": "Aramis", "dominio": "www.aramis.com.br"},
        {"marca": "Reserva", "dominio": "www.usereserva.com"},
        {"marca": "Tommy Hilfiger", "dominio": "br.tommy.com"},
    ]

    arvore_geral = {}

    for alvo in concorrentes:
        categorias = await extrair_arvore_categorias(alvo["marca"], alvo["dominio"])

        # Filtro Avançado: Bloqueando lixo comercial e categorias femininas/pets
        palavras_bloqueadas = [
            "liquida",
            "outlet",
            "sale",
            "gift",
            "presente",
            "bazar",
            "home",
            "casa",
            "livro",
            "feminino",
            "mulher",
            "menina",
            "saia",
            "vestido",
            "top",
            "pets",
            "cosmeticos",
        ]

        categorias_limpas = []

        for cat in categorias:
            url_lower = cat["url"].lower()
            nome_lower = cat["nome"].lower()

            # 1. Regra de Bloqueio Universal (Se tiver palavra de mulher, pet ou lixo, descarta)
            if any(
                bad_word in url_lower or bad_word in nome_lower
                for bad_word in palavras_bloqueadas
            ):
                continue

            # 2. Regras Específicas por Marca
            if alvo["marca"] == "Reserva":
                # A Reserva tem as rotas muito bem definidas. Só passa se for expressamente masculino, infantil ou bebê.
                if not any(
                    termo_alvo in url_lower
                    for termo_alvo in ["/masculino", "/infantil", "/bebe"]
                ):
                    continue

            # Se sobreviveu aos filtros, é masculino ou infantil!
            categorias_limpas.append(cat)

        arvore_geral[alvo["marca"]] = categorias_limpas

        print(
            f"[{alvo['marca']}] Salvando {len(categorias_limpas)} categorias após limpeza."
        )

    # Salva o arquivo de configuração de rotas
    nome_arquivo = "taxonomia_concorrentes.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(arvore_geral, f, indent=2, ensure_ascii=False)

    print(
        f"\nMapeamento Concluído! O arquivo '{nome_arquivo}' está pronto para alimentar o nosso Spider focado no público Masculino e Infantil."
    )


if __name__ == "__main__":
    asyncio.run(main())
