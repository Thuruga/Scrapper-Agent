"""
Bootstrap do Intelligence Scraper.

Inicia a aplicação FastAPI, carrega middlewares e rotas, e expõe o frontend estático.
"""

import sys
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from api import api_router, public_router

# Configuração global de logs para ambiente Enterprise
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout
)
logger = logging.getLogger("App")

# O WindowsProactorEventLoopPolicy já é o padrão no Python 3.8+ e está deprecado no 3.16.
# Portanto, não precisamos forçar a alteração da política de event loop no Windows.


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: carrega dados persistentes
    from services.brand_service import brand_service
    from services.price_monitor_service import monitor_service

    # Supabase (se configurado) — seed automático se tabela vazia
    brand_service.load_from_supabase()

    # Monitores de preço (arquivo local — efêmeros por design)
    monitor_service.load_monitors()
    yield
    # Shutdown (opcional)

app = FastAPI(
    title="Intelligence Scraper API",
    description="API robusta para extração de dados da Camada Bronze.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS — dynamic origins for split deploy
_origins = (
    ["*"]
    if settings.ALLOWED_ORIGINS == "*"
    else [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware to disable caching during development
@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response






# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
# Router público: WebSocket (/ws/{job_id}) — sem autenticação HTTP obrigatória
app.include_router(public_router)

# Endpoints protegidos por X-API-Key
app.include_router(api_router)

@app.get("/health-check")
async def health_check():
    return {"status": "ok", "message": "Backend is alive"}

@app.get("/download-report/{filename}")
async def download_report(filename: str):
    """Serve um relatório gerado para download direto."""
    # Previne path traversal e restringe a extensões conhecidas (excel/csv)
    if "/" in filename or "\\" in filename or not filename.endswith((".xlsx", ".csv")):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not os.path.exists(filename):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(filename, filename=filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ---------------------------------------------------------------------------
# Frontend (React Build) — skipped on Render (split deploy)
# ---------------------------------------------------------------------------
import os as _os

if not settings.RENDER:
    @app.get("/")
    async def read_index():
        return FileResponse("frontend/dist/index.html")

    if _os.path.isdir("frontend/dist/assets"):
        app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
    if _os.path.isdir("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.info("RENDER=true — frontend static mount disabled (split deploy)")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)

