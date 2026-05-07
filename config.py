"""
Configurações centralizadas do Intelligence Scraper.

Carrega variáveis do arquivo .env e fornece defaults robustos.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Identidade e Evasão (Anti-Bot)
# ---------------------------------------------------------------------------
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]


# ---------------------------------------------------------------------------
# Brand Registry — [DEPRECATED]
# Agora as marcas são geridas dinamicamente via brand_service e data/brands.json
# ---------------------------------------------------------------------------
# BRAND_REGISTRY removido para evitar múltiplas fontes de verdade.


class Settings(BaseSettings):
    """Configurações carregadas de .env com fallback para defaults."""

    # Server
    APP_HOST: str = "localhost"
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

    # Evasão e Robustez
    ENABLE_PROXY: bool = Field(default=False, description="Habilita uso de proxies.")
    PROXY_LIST: List[str] = Field(
        default_factory=list,
        description="Lista de proxies no formato ['http://user:pass@ip:port', ...]",
    )
    
    # Advanced Proxy Services
    BRIGHTDATA_PROXY_URL: Optional[str] = Field(default=None, description="URL do proxy BrightData.")
    SCRAPERAPI_KEY: Optional[str] = Field(default=None, description="Chave de API do ScraperAPI.")
    
    # Security
    SCRAPER_API_KEY: str = Field(default="dev-key-123", description="Chave de API para proteger os endpoints.")
    
    USER_AGENTS: List[str] = Field(
        default_factory=lambda: DEFAULT_USER_AGENTS,
        description="Lista de User-Agents para rotação.",
    )
    REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_RETRIES: int = 3

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Instância singleton usada por toda a aplicação
settings = Settings()
