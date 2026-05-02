"""
Configurações centralizadas do Intelligence Scraper.

Carrega variáveis do arquivo .env e fornece defaults robustos.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict


# ---------------------------------------------------------------------------
# Brand Registry — Mapeamento de marcas → domínios e URLs base
# ---------------------------------------------------------------------------
BRAND_REGISTRY: Dict[str, dict] = {
    "aramis": {
        "name": "Aramis",
        "domain": "www.aramis.com.br",
        "base_url": "https://www.aramis.com.br",
    },
    "reserva": {
        "name": "Reserva",
        "domain": "www.usereserva.com",
        "base_url": "https://www.usereserva.com",
    },
    "tommy": {
        "name": "Tommy Hilfiger",
        "domain": "br.tommy.com",
        "base_url": "https://br.tommy.com",
    },
}


class Settings(BaseSettings):
    """Configurações carregadas de .env com fallback para defaults."""

    # Server
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # VTEX Catalog Cache
    VTEX_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="Tempo de vida do cache de categorias em segundos (default: 1h).",
    )

    # Scraper tuning
    MAX_CONCURRENCY: int = Field(
        default=3,
        description="Número máximo de scrapers rodando em paralelo.",
    )
    SCRAPER_DELAY_SECONDS: float = Field(
        default=2.0,
        description="Pausa entre extrações para simular comportamento humano.",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Instância singleton usada por toda a aplicação
settings = Settings()
