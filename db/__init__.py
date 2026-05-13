"""
Cliente Supabase — camada de persistência externa.

Se SUPABASE_URL e SUPABASE_KEY estiverem definidos no ambiente, usa Supabase.
Caso contrário, retorna None e o brand_service cai no modo JSON local (dev).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("DB")

# SQL de criação da tabela (executar manualmente no Supabase dashboard)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS brands (
    brand_key       TEXT PRIMARY KEY,
    brand_name      TEXT NOT NULL,
    domain          TEXT NOT NULL,
    review_provider TEXT DEFAULT 'none',
    review_store_id TEXT,
    vtex_account    TEXT,
    engine          TEXT DEFAULT 'vtex',
    logo_url        TEXT,
    mappings        JSONB DEFAULT '[]'::jsonb,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

_client = None


def get_supabase_client():
    """Retorna o cliente Supabase ou None se não configurado."""
    global _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    if _client is None:
        try:
            from supabase import create_client

            _client = create_client(url, key)
            logger.info("[DB] Supabase conectado com sucesso.")
        except ImportError:
            logger.warning("[DB] Pacote 'supabase' não instalado. Usando JSON local.")
            return None
        except Exception as e:
            logger.error(f"[DB] Falha ao conectar no Supabase: {e}")
            return None

    return _client
