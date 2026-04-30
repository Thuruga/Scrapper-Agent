import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict
import importlib
import os

app = FastAPI(title="E-commerce Scraper API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str
    brand: str


from fastapi import WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import uuid

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        if job_id in self.active_connections:
            del self.active_connections[job_id]

    async def send_message(self, message: dict, job_id: str):
        if job_id in self.active_connections:
            await self.active_connections[job_id].send_json(message)

manager = ConnectionManager()

@app.post("/scrape")
async def scrape_product(request: ScrapeRequest):
    brand_map = {"aramis": "aramis", "reserva": "reserva", "tommy": "tommy"}

    module_name = brand_map.get(request.brand.lower())
    if not module_name:
        raise HTTPException(status_code=400, detail="Brand not supported")

    def run_scraper():
        import asyncio
        import sys
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return asyncio.run(module.scrape_competitor_product(request.url, request.brand))

    try:
        module = importlib.import_module(module_name)
        result = await run_in_threadpool(run_scraper)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to scrape product")

        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_orchestrator_sync(job_id: str, url: str, brand: str, main_loop: asyncio.AbstractEventLoop):
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    from orquestrador import run_orchestrator
    
    def log_callback(msg):
        asyncio.run_coroutine_threadsafe(manager.send_message(msg, job_id), main_loop)
        
    asyncio.run(run_orchestrator(marca=brand, url_categoria=url, log_callback=log_callback))
    # Envia evento de encerramento da conexão pelo servidor se necessário
    # asyncio.run_coroutine_threadsafe(manager.send_message({"type": "close"}, job_id), main_loop)

@app.post("/scrape-category")
async def scrape_category(request: ScrapeRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    main_loop = asyncio.get_running_loop()
    background_tasks.add_task(run_orchestrator_sync, job_id, request.url, request.brand, main_loop)
    return {"job_id": job_id, "message": "Orquestração iniciada."}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await manager.connect(websocket, job_id)
    try:
        while True:
            # Mantém a conexão aberta esperando mensagens do cliente (ping/pong)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)


# Serve Frontend
@app.get("/")
async def read_index():
    return FileResponse("index.html")


# Mount other static files
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
