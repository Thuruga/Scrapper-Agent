"""
Bootstrap do Intelligence Scraper.

Inicia a aplicação FastAPI, carrega middlewares e rotas, e expõe o frontend estático.
"""

import asyncio
import sys

# Corrige problema de event loop no Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from api import api_router


# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Intelligence Scraper API",
    description="API robusta para extração de dados da Camada Bronze.",
    version="2.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
# Registra todos os endpoints da API sob o prefixo principal (ou sem prefixo)
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Frontend Estático
# ---------------------------------------------------------------------------
@app.get("/")
async def read_index():
    return FileResponse("index.html")


app.mount("/", StaticFiles(directory=".", html=True), name="static")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
