"""Bootstrap local da API e do build opcional do frontend."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import api_router, public_router
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("App")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega os dados locais e inicia os monitores agendados."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from services.category_monitor_service import category_monitor_job
    from services.price_monitor_service import monitor_service

    monitor_service.load_monitors()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(category_monitor_job, "interval", minutes=10)
    scheduler.start()
    logger.info("Monitor de categorias iniciado (intervalo de 10 minutos).")

    yield
    scheduler.shutdown()


app = FastAPI(
    title="Intelligence Scraper API",
    description="API local para extracao e comparacao de produtos.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.include_router(public_router)
app.include_router(api_router)


@app.get("/health-check")
async def health_check():
    return {"status": "ok", "mode": "local"}


@app.get("/download-report/{filename}")
async def download_report(filename: str):
    """Serve um relatorio gerado localmente."""
    if "/" in filename or "\\" in filename or not filename.endswith((".xlsx", ".csv")):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(filename):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        filename,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Um build local pode ser servido pelo backend; no desenvolvimento, use o Vite.
_frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
_frontend_index = _frontend_dist / "index.html"

if _frontend_index.is_file():

    @app.get("/")
    async def read_index():
        return FileResponse(_frontend_index)

    if (_frontend_dist / "assets").is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=_frontend_dist / "assets"),
            name="assets",
        )
else:

    @app.get("/")
    async def local_frontend_hint():
        return {"message": "Backend em :8500 — Frontend local em http://127.0.0.1:5173"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)
