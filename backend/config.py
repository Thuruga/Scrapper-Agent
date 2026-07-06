"""
Configurações centralizadas do Intelligence Scraper.

Carrega variáveis do arquivo .env e fornece defaults robustos.
Todos os hiperparâmetros de relevância cross-marketplace ficam aqui —
nenhum número mágico nos serviços.
"""

import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Literal, Optional

logger = logging.getLogger("config")

# Diretório base usado pelos arquivos locais de configuração e dados.
BASE_DIR = Path(__file__).resolve().parent


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
    APP_HOST: Literal["127.0.0.1", "localhost", "::1"] = "127.0.0.1"
    APP_PORT: int = 8500

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
    BRIGHTDATA_PROXY_URL: Optional[str] = Field(default=None, description="URL do proxy BrightData (ex: http://user-zone-residential:pass@brd.superproxy.io:22225).")
    SCRAPERAPI_KEY: Optional[str] = Field(default=None, description="Chave de API do ScraperAPI — gateway com CAPTCHA solving integrado.")

    # Proxy health
    PROXY_FAILURE_THRESHOLD: int = Field(
        default=3,
        description="Número de falhas consecutivas antes de blacklistar um proxy.",
    )
    PROXY_BLACKLIST_SECONDS: int = Field(
        default=300,
        description="Tempo em segundos que um proxy permanece blacklistado após falhas.",
    )

    # Security — API Key simples (sem login/JWT)
    INTERNAL_API_KEY: str = Field(
        default="dev-api-key",
        description="Chave enviada pelo frontend local em X-API-Key.",
    )
    # [Legado] mantido para não quebrar referências em código antigo
    # Playwright
    PLAYWRIGHT_ENABLED: bool = Field(
        default=True,
        description="False desabilita os fallbacks que precisam de Chromium.",
    )

    USER_AGENTS: List[str] = Field(
        default_factory=lambda: DEFAULT_USER_AGENTS,
        description="Lista de User-Agents para rotação.",
    )
    REQUEST_TIMEOUT_SECONDS: int = Field(default=20, description="Timeout HTTP em segundos.")
    MAX_RETRIES: int = Field(default=3, description="[Legado] Use RETRY_MAX_ATTEMPTS.")

    # Retry Policy
    RETRY_MAX_ATTEMPTS: int = Field(
        default=3,
        description="Número máximo de tentativas por requisição (inclui a primeira).",
    )
    RETRY_BASE_SECONDS: float = Field(
        default=1.0,
        description="Base do backoff exponencial em segundos.",
    )
    RETRY_MAX_SECONDS: float = Field(
        default=30.0,
        description="Cap máximo do backoff em segundos.",
    )

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5,
        description="Falhas consecutivas para abrir o circuit breaker de um engine.",
    )
    CIRCUIT_BREAKER_TIMEOUT_SECONDS: int = Field(
        default=60,
        description="Tempo em segundos que o circuit breaker permanece aberto.",
    )

    # CEP Default
    DEFAULT_CEP: str = Field(
        default="01415000",
        description="CEP padrão usado como fallback no cálculo de frete.",
    )

    # Phase 44 - Ruptura de estoque, cart-probe controlado e reviews sob demanda
    MAX_REVIEW_PAGES: int = Field(
        default=2,
        description="Limite conservador de paginas de comentarios buscadas sob demanda.",
    )
    STOCK_PROBE_QUANTITY: int = Field(
        default=999,
        description="Quantidade usada no cart-probe controlado de profundidade de estoque.",
    )
    STOCK_PROBE_THROTTLE_SECONDS: float = Field(
        default=2.0,
        description="Throttle fixo entre probes de profundidade de estoque.",
    )
    STOCK_PROBE_TIMEOUT_SECONDS: int = Field(
        default=8,
        description="Timeout curto para cada probe controlado de profundidade de estoque.",
    )
    MAX_STOCK_DEPTH_PROBES_PER_BRAND: int = Field(
        default=3,
        description="Limite conservador de probes de profundidade por marca/execucao.",
    )

    # Phase 45 - Analise de sortimento independente
    SORTIMENT_CRON_INTERVAL_MINUTES: int = Field(
        default=60,
        description="Cadencia propria do cron de sortimento, separada do monitor de 10 minutos.",
    )
    SORTIMENT_MAX_PRODUCTS_PER_CATEGORY: int = Field(
        default=1000,
        description="Teto de produtos coletados por categoria em cada snapshot de sortimento.",
    )
    SORTIMENT_EVIDENCE_PER_BUCKET: int = Field(
        default=3,
        description="Quantidade maxima de evidencias leves persistidas por bucket de sortimento.",
    )

    # Phase 42 - Matriz de frete multi-regional (FRET-09)
    SHIPPING_MATRIX_THROTTLE_SECONDS: float = Field(
        default=2.0,
        description="Throttle fixo entre chamadas de frete da matriz regional (uma por CEP).",
    )
    SHIPPING_MATRIX_CACHE_TTL_SECONDS: int = Field(
        default=21600,
        description="TTL do cache (produto, CEP) da matriz regional — 6h default, curto por D-09.",
    )

    model_config = {
        "env_file": BASE_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

# ---------------------------------------------------------------------------
# Relevância Cross-Marketplace
# Todos os hiperparâmetros do pipeline de scoring são configuráveis via .env
# sem necessidade de alterar código.
# ---------------------------------------------------------------------------
class RelevanceSettings(BaseSettings):
    """Parâmetros do pipeline de relevância cross-marketplace."""

    # ---- Thresholds de corte ------------------------------------------------
    CROSS_MIN_SCORE_WITH_VISION: float = Field(
        default=60.0,
        description="Score mínimo (0-100) quando a IA visual (CLIP) está ativa.",
    )
    CROSS_MIN_SCORE_WITHOUT_VISION: float = Field(
        default=55.0,
        description="Score mínimo (0-100) quando não há imagem de referência (só NLP).",
    )
    CROSS_MAX_RESULTS_PER_ENGINE: int = Field(
        default=30,
        description="Máximo de produtos buscados por motor antes do filtro NLP.",
    )
    CROSS_MAX_RESULTS_PER_PLATFORM_FINAL: int = Field(
        default=10,
        description="Máximo de produtos exibidos por plataforma no resultado final.",
    )

    # ---- Fallback "produtos similares" (S1) ---------------------------------
    # Quando o filtro estrito (brand gate + corte) zera TODOS os resultados — caso
    # típico de marca própria (ex: Aramis) que não é revendida nos marketplaces —
    # exibe produtos similares de categoria em vez de uma lista vazia.
    CROSS_SIMILAR_FALLBACK_ENABLED: bool = Field(
        default=True,
        description=(
            "Quando True e o filtro estrito não retorna NENHUM produto, refaz o filtro "
            "sem o brand gate e com corte CROSS_SIMILAR_MIN_SCORE para exibir similares. "
            "Preserva a precisão quando há match exato; degrada para 'similares' quando não há."
        ),
    )
    CROSS_SIMILAR_MIN_SCORE: float = Field(
        default=15.0,
        description=(
            "Corte de score (0-100) usado SOMENTE no fallback de produtos similares. "
            "Mais baixo que o corte estrito porque candidatos de outra marca recebem "
            "penalidade de marca/model-words e pontuam ~15-25 mesmo sendo da mesma categoria."
        ),
    )

    # ---- Gate de marca (BRAND-02 / BRAND-03) --------------------------------
    BRAND_GATE_ENABLED: bool = Field(
        default=True,
        description=(
            "Quando True, descarta itens cujo título não contém nenhuma das "
            "marcas conhecidas presentes na query. No-op se a query não "
            "especifica marca conhecida. Configurável via .env "
            "(BRAND_GATE_ENABLED=false para desativar)."
        ),
    )

    # ---- Discriminação de modelo visual (MODEL-02) --------------------------
    VISUAL_TIEBREAK_ENABLED: bool = Field(
        default=True,
        description=(
            "Quando True, candidatos da mesma marca com scores de texto dentro "
            "de VISUAL_TIEBREAK_TEXT_WINDOW são reordenados pelo score visual "
            "(CLIP). Rollback: VISUAL_TIEBREAK_ENABLED=false desativa sem "
            "alterar código."
        ),
    )
    VISUAL_TIEBREAK_TEXT_WINDOW: float = Field(
        default=10.0,
        description=(
            "Janela de ambiguidade de texto (pontos 0-100): candidatos da mesma "
            "marca dentro desta faixa do top-score da marca são reordenados pelo "
            "score visual. Default 10.0 cobre a dispersão típica de variantes de "
            "cor (~5.3 pontos) mais candidatos de modelo adjacente (~8 pontos); "
            "tunável via .env — marcado para recalibração após uso real em "
            "categorias além de polo."
        ),
    )

    # ---- Pesos do score de texto (NLP) --------------------------------------
    # Devem somar 1.0
    NLP_WRATIO_WEIGHT: float = Field(
        default=0.50,
        description="Peso do WRatio (lenient) no score de texto.",
    )
    NLP_TOKEN_SORT_WEIGHT: float = Field(
        default=0.20,
        description="Peso do token_sort_ratio (strict) no score de texto.",
    )
    NLP_PARTIAL_SET_WEIGHT: float = Field(
        default=0.30,
        description="Peso do partial_token_set_ratio (forgiving) no score de texto.",
    )

    # ---- Pesos do score final (texto + imagem) -------------------------------
    # Devem somar 1.0
    FINAL_TEXT_WEIGHT: float = Field(
        default=0.60,
        description="Peso do NLP no score final quando vision está ativa.",
    )
    FINAL_IMAGE_WEIGHT: float = Field(
        default=0.40,
        description="Peso da IA visual (CLIP) no score final.",
    )

    # ---- Penalidades de model-words ----------------------------------------
    NLP_MODEL_PENALTY_LOW_THRESHOLD: float = Field(
        default=0.50,
        description="Taxa de acerto de model_words abaixo da qual aplica penalidade pesada.",
    )
    NLP_MODEL_PENALTY_MED_THRESHOLD: float = Field(
        default=0.75,
        description="Taxa de acerto de model_words abaixo da qual aplica penalidade moderada.",
    )
    NLP_MODEL_PENALTY_HEAVY_WITHOUT_BRAND: float = Field(
        default=0.55,
        description="Multiplicador de penalidade pesada quando marca NÃO está presente.",
    )
    NLP_MODEL_PENALTY_HEAVY_WITH_BRAND: float = Field(
        default=0.40,
        description=(
            "Multiplicador de penalidade pesada quando marca está presente e model_ratio < LOW_THRESHOLD. "
            "Reforçado na Phase 23 (MODEL-01): 0.70 → 0.40 para empurrar o texto penalizado de candidatos "
            "de modelo divergente (mesma marca) abaixo de MED_TEXT_FLOOR (40), defeatando o resgate do "
            "Gate 1 visual. Decisão de planner: 0.40 é o limite conservador — 99*0.40=39.6 < 40 cobre "
            "todo blend bruto realista; 0.45 falharia já em blend 90 (90*0.45=40.5 >= 40)."
        ),
    )
    NLP_MODEL_PENALTY_MED_WITHOUT_BRAND: float = Field(
        default=0.80,
        description="Multiplicador de penalidade moderada quando marca NÃO está presente.",
    )
    NLP_MODEL_PENALTY_MED_WITH_BRAND: float = Field(
        default=0.75,
        description=(
            "Multiplicador de penalidade moderada quando marca está presente e "
            "LOW_THRESHOLD <= model_ratio < MED_THRESHOLD. "
            "Reforçado na Phase 23 (MODEL-01): 0.90 → 0.75 para a faixa MED (0.50 <= ratio < 0.75). "
            "Mais discriminante que 0.90, mas por desenho NÃO bloqueia totalmente o resgate visual — "
            "a ambiguidade residual é tratada pelo desempate visual (MODEL-02, Plan 02)."
        ),
    )

    # ---- Penalty de categoria divergente ------------------------------------
    NLP_CATEGORY_PENALTY_HIGH_SCORE: float = Field(
        default=0.75,
        description="Multiplicador quando categoria diverge e score base > 0.85.",
    )
    NLP_CATEGORY_PENALTY_LOW_SCORE: float = Field(
        default=0.55,
        description="Multiplicador quando categoria diverge e score base <= 0.85.",
    )
    NLP_CATEGORY_HIGH_SCORE_THRESHOLD: float = Field(
        default=0.85,
        description="Limiar de score acima do qual a penalidade de categoria é suavizada.",
    )

    # ---- Vocabulário --------------------------------------------------------
    NLP_VOCABULARY_PATH: str = Field(
        default="data/nlp_vocabulary.json",
        description="Caminho relativo ao diretório raiz do projeto para o arquivo de vocabulário NLP.",
    )

    # ---- Engines: Netshoes --------------------------------------------------
    NETSHOES_GENDER_FILTER: str = Field(
        default="masculino",
        description="Filtro de gênero aplicado na URL da Netshoes. Use '' para desabilitar.",
    )

    # ---- Engines: Mercado Livre ---------------------------------------------
    ML_CATEGORY_PATH: str = Field(
        default="calcados-roupas-bolsas/masculino",
        description="Subpath de categoria na URL do Mercado Livre (após lista.mercadolivre.com.br/).",
    )
    ML_TIMEOUT_PLAYWRIGHT_SECONDS: float = Field(
        default=100.0,
        description=(
            "Orçamento TOTAL (no cross) para o motor do Mercado Livre, que roda SEQUENCIAL dentro "
            "do mesmo asyncio.wait_for: curl_cffi (até ML_TIMEOUT_CURL_SECONDS=15s) ANTES do "
            "fallback Playwright (goto networkidle até 60s + extra_sleep 10s + launch/retry ~7s). "
            "Pior caso ~92s — por isso 100s: garante que o wait_for não cancele o motor (deixando "
            "Chromium órfão) justo quando o Playwright ia resolver o Anubis."
        ),
    )
    ML_TIMEOUT_CURL_SECONDS: float = Field(
        default=15.0,
        description="Timeout para o Mercado Livre via curl_cffi.",
    )

    # ---- Engines: timeout genérico ------------------------------------------
    ENGINE_DEFAULT_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        description="Timeout padrão para motores não-Playwright.",
    )

    # ---- Engines: Amazon ----------------------------------------------------
    PLAYWRIGHT_AMAZON_FALLBACK: bool = Field(
        default=True,
        description=(
            "True ativa o Playwright como fallback na Amazon quando curl_cffi "
            "retorna CAPTCHA (503). Desabilite em ambientes sem Chromium."
        ),
    )

    model_config = {
        "env_file": BASE_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "env_prefix": "",
    }


# Instância singleton usada por toda a aplicação
settings = Settings()
relevance_settings = RelevanceSettings()
