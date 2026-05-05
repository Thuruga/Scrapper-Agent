from curl_cffi.requests import AsyncSession
from typing import List, Dict, Any
import json
import re


async def fetch_vtex_categories(domain: str, depth: int = 3) -> List[Dict[str, Any]]:
    """
    Motor de extração com Auto-Discovery do nome da conta VTEX.
    Perfeito para contornar setups Headless/FastStore sem depender de input manual.
    """
    domain = domain.replace("https://", "").replace("http://", "").strip("/")
    url_principal = f"https://{domain}/api/catalog_system/pub/category/tree/{depth}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        async with AsyncSession(impersonate="chrome", timeout=15) as session:
            print(f"📥 Tentando domínio principal: {url_principal}")
            response = await session.get(url_principal, headers=headers)

            conteudo_bruto = response.text

            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    print("⚠️ O frontend devorou a requisição (Retornou HTML).")
            else:
                print(f"⚠️ Status HTTP {response.status_code} no domínio principal.")

            # ─── MÓDULO DE AUTO-DISCOVERY (O "Pulo do Gato") ───
            print("🔍 Inspecionando o HTML para descobrir o ID real da conta VTEX...")

            # Caça qualquer URL da CDN da VTEX dentro do HTML para extrair o nome verdadeiro da conta
            vtexassets_match = re.search(
                r"https:\/\/([^.]+)\.vtexassets\.com", conteudo_bruto
            )

            if vtexassets_match:
                account_name = vtexassets_match.group(1)
                print(
                    f"🎯 Bingo! Conta VTEX descoberta no código-fonte: '{account_name}'"
                )
            else:
                # Fallback de segurança se não encontrar a CDN no HTML
                account_match = re.search(r"^(?:www\.)?([^.]+)", domain)
                account_name = (
                    account_match.group(1) if account_match else domain.split(".")[0]
                )
                print(
                    f"⚠️ CDN não encontrada. A inferir a conta pelo domínio: '{account_name}'"
                )

            url_fallback = f"https://{account_name}.vtexcommercestable.com.br/api/catalog_system/pub/category/tree/{depth}"

            # ─── TENTATIVA 2: Fallback Certeiro ───
            print(f"🔄 Acionando Fallback Oculto: {url_fallback}")
            response_fb = await session.get(url_fallback, headers=headers)

            if response_fb.status_code == 200:
                try:
                    dados = response_fb.json()
                    print("✅ Sucesso! Conectado diretamente ao Backend da VTEX.")
                    return dados
                except json.JSONDecodeError:
                    print("❌ Falha: O Fallback oculto também retornou HTML.")
                    return []
            else:
                print(f"❌ O Fallback falhou com Status HTTP {response_fb.status_code}")
                return []

    except Exception as e:
        print(f"❌ Erro crítico de rede: {e}")
        return []
