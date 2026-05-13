# 🚀 Deploy Enterprise Zero Cost — Intelligence Scraper

Guia para publicar o projeto como site sem gastar nada, com qualidade comercial.
Arquitetura: **Vercel** (frontend) + **Render** (backend) + **Supabase** (banco de dados).

---

## Arquitetura

```
┌─────────────┐   X-API-Key    ┌──────────────┐   SQL      ┌─────────────┐
│   Vercel    │ ─────────────→ │   Render     │ ─────────→ │  Supabase   │
│  (Frontend) │                │  (Backend)   │            │ (PostgreSQL)│
│  React SPA  │                │  FastAPI +   │            │  Dados      │
│  CDN Global │                │  Playwright  │            │  Persistidos│
└─────────────┘                └──────────────┘            └─────────────┘
   Sempre online                750h/mês grátis             500MB grátis
   Sem dormência                Dorme após 15min*            Sempre online
```
> *O keep-alive resolve o problema de dormência — veja Passo 4.

---

## Passo 0: Supabase (Banco de Dados)

1. Acesse [supabase.com](https://supabase.com) → **New Project** (grátis, sem cartão)
2. Defina nome, senha e região (escolha **South America - São Paulo**)
3. No painel, vá em **SQL Editor** e execute:

```sql
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
```

4. Em **Settings → API**, anote:
   - **Project URL** → será `SUPABASE_URL`
   - **anon public key** → será `SUPABASE_KEY`

> ✅ Na primeira inicialização do backend, o `brands.json` local será importado automaticamente (seed).

---

## Passo 1: Deploy do Backend (Render)

1. Acesse [render.com](https://render.com) → crie conta (grátis, sem cartão)
2. **New → Web Service** → conecte o repo `Thuruga/Scrapper-Agent`
3. Configure:
   - **Runtime:** Python
   - **Build Command:**
     ```
     pip install -r requirements.txt && playwright install --with-deps chromium
     ```
   - **Start Command:**
     ```
     uvicorn app:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** Free

4. Variáveis de ambiente (**Environment** tab):

| Variável | Valor |
|----------|-------|
| `RENDER` | `true` |
| `INTERNAL_API_KEY` | *(gere um UUID: `python -c "import uuid; print(uuid.uuid4())"`)* |
| `SUPABASE_URL` | *(URL do projeto Supabase — Passo 0)* |
| `SUPABASE_KEY` | *(anon key do Supabase — Passo 0)* |
| `ALLOWED_ORIGINS` | *(preencher após Passo 2, ex: `https://scrapper-agent.vercel.app`)* |
| `PLAYWRIGHT_ENABLED` | `true` *(mude para `false` se o servidor cair por OOM)* |

5. **Create Web Service** → aguarde o deploy (~5-8min)
6. Anote a URL: `https://scrapper-agent.onrender.com`

---

## Passo 2: Deploy do Frontend (Vercel)

1. Acesse [vercel.com](https://vercel.com) → crie conta com GitHub
2. **Add New → Project** → importe `Thuruga/Scrapper-Agent`
3. Configure:
   - **Root Directory:** `frontend`
   - **Framework:** Vite
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`

4. Variáveis de ambiente:

| Variável | Valor |
|----------|-------|
| `VITE_API_URL` | `https://scrapper-agent.onrender.com` |
| `VITE_API_KEY` | *(o mesmo valor de `INTERNAL_API_KEY` do Render)* |

5. **Deploy** → anote a URL: `https://scrapper-agent.vercel.app`

---

## Passo 3: Conectar Frontend ↔ Backend

1. Volte ao **Render** → seu service → **Environment**
2. Atualize `ALLOWED_ORIGINS` com a URL do Vercel:
   ```
   https://scrapper-agent.vercel.app
   ```
3. O Render fará redeploy automático

---

## Passo 4: Keep-Alive (Elimina o Cold Start)

O Render free "dorme" após 15 minutos sem tráfego. Configure um ping externo gratuito:

### Opção A — UptimeRobot (Recomendado)
1. Acesse [uptimerobot.com](https://uptimerobot.com) → crie conta grátis
2. **Add New Monitor:**
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** `Scrapper Agent Keep-Alive`
   - **URL:** `https://scrapper-agent.onrender.com/health-check`
   - **Monitoring Interval:** **5 minutes**
3. Salve → ✅ O servidor nunca dormirá

### Opção B — Cron-job.org
1. Acesse [cron-job.org](https://cron-job.org) → crie conta grátis
2. **Create cronjob:**
   - **URL:** `https://scrapper-agent.onrender.com/health-check`
   - **Schedule:** Every 14 minutes
3. Salve

> ⚡ Com o keep-alive ativo, o primeiro acesso do comercial é instantâneo — sem cold start.

---

## Limitações do Free Tier

| Aspecto | Vercel (Frontend) | Render (Backend) | Supabase (DB) |
|---------|------------------|------------------|----------------|
| **Disponibilidade** | Sempre online | Sempre* (com keep-alive) | Sempre online |
| **RAM** | N/A | 512MB | N/A |
| **Disco** | N/A | Efêmero (irrelevante — dados no Supabase) | 500MB |
| **Requests** | 100GB bandwidth | Ilimitados | 50.000/dia |
| **Playwright** | N/A | ⚠️ 300-500MB RAM | N/A |

> ⚠️ **Playwright + OOM:** Se dois usuários rodarem scraping simultaneamente e o servidor cair,
> defina `PLAYWRIGHT_ENABLED=false` no Render. O sistema usará `curl_cffi` (leve) como engine principal.
> Playwright continuará funcionando localmente.

---

## Desenvolvimento Local

Nada muda — continua igual:

```bash
# Backend
python app.py

# Frontend (outro terminal)
cd frontend
npm run dev
```

O `.env` local usa `VITE_API_KEY=dev-api-key` que bate com `INTERNAL_API_KEY=dev-api-key` do backend.
Sem Supabase local: usa `data/brands.json` automaticamente.
