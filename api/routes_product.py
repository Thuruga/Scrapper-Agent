import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from services.price_monitor_service import monitor_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class MonitorStartRequest(BaseModel):
    url: str
    brand: str
    interval: int = 10  # minutos
    duration: int = 24  # horas


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/monitor/start")
async def start_monitoring(request: MonitorStartRequest):
    """Inicia o monitoramento de um produto."""
    job_id = str(uuid.uuid4())
    
    # Inicia o monitoramento em background
    try:
        config = await monitor_service.start_monitor(
            job_id=job_id,
            url=request.url,
            brand=request.brand,
            interval=request.interval,
            duration=request.duration
        )
        return {"job_id": job_id, "status": "started", "config": config.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/stop/{job_id}")
async def stop_monitoring(job_id: str):
    """Interrompe um monitoramento ativo."""
    await monitor_service.stop_monitor(job_id)
    return {"status": "stopped"}


@router.get("/monitor/history/{job_id}")
async def get_monitor_history(job_id: str):
    """Retorna o histórico de um monitor específico."""
    if job_id not in monitor_service.monitors:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor_service.monitors[job_id].model_dump()

